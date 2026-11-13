"""Správce MDT, pozvánky, komise a lékaři z jiných nemocnic (T-361, T-362, D-027, docs/UCTY_A_PVW.md)."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.mdt import roles
from apps.mdt.models import Committee, Invitation, MdtCase, MdtSession

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')
    return fake_fhir_dataset


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def with_jwt(user):
    """Přihlášení přes JWT cookie jako v prohlížeči: middleware rozsahu externích lékařů běží před DRF."""
    client = APIClient()
    client.cookies['access_token'] = str(RefreshToken.for_user(user).access_token)
    return client


INVITE = {'last_name': 'Malá', 'first_name': 'Eva', 'title_before': 'MUDr.', 'specialty': 'radiologist',
          'role': 'mdt_viewer', 'email': 'eva.mala@nemocnice.test'}


def invite(body=None, username='predseda'):
    r = as_user(username).post('/api/mdt/invitations/', {**INVITE, **(body or {})}, format='json')
    assert r.status_code == 201, r.json()
    return r.json()


def token_of(link: str) -> str:
    return link.rsplit('/', 1)[1]


def accept(token, username='mala', password='Silne-heslo-2026'):
    return APIClient().post(f'/api/mdt/invitations/public/{token}/accept/',
                            {'username': username, 'password': password, 'password2': password}, format='json')


def test_demo_chair_is_also_manager(seeded):
    assert as_user('predseda').get('/api/mdt/me/').json()['is_manager'] is True
    me = as_user('onkolog').get('/api/mdt/me/').json()
    assert (me['is_manager'], me['is_external'], me['onboarding_done'], me['organization']) == (False, False, True, '')
    assert me['committees'] and all({'id', 'name'} == set(c) for c in me['committees'])


def test_only_manager_manages_invitations_and_users(seeded):
    for user in ('onkolog', 'chirurg'):
        assert as_user(user).post('/api/mdt/invitations/', INVITE, format='json').status_code == 403
        assert as_user(user).get('/api/mdt/invitations/').status_code == 403
    chair = get_user_model().objects.get(username='predseda')
    roles.set_manager(chair, False)                        # předseda bez role správce účty nespravuje (Q29)
    assert as_user('predseda').post('/api/mdt/invitations/', INVITE, format='json').status_code == 403
    uid = get_user_model().objects.get(username='chirurg').pk
    assert as_user('predseda').patch(f'/api/mdt/users/{uid}/', {'specialty': 'surgeon'}, format='json').status_code == 403
    assert as_user('predseda').post('/api/mdt/sessions/', {'date': '2026-12-01T14:00:00+01:00', 'title': 'X'},
                                    format='json').status_code == 201     # zasedání dál zakládá předseda


def test_invitation_link_is_single_use_and_creates_account(seeded):
    committee = Committee.objects.first()
    created = invite({'committees': [committee.pk]})
    assert created['status'] == 'pending' and created['email_sent'] is True
    assert created['path'] == f"/pozvanka/{token_of(created['link'])}"
    assert len(mail.outbox) == 1 and created['link'] in mail.outbox[0].body
    token = token_of(created['link'])
    assert not Invitation.objects.filter(token_hash=token).exists()        # v databázi jen hash
    public = APIClient().get(f'/api/mdt/invitations/public/{token}/').json()
    assert (public['last_name'], public['specialty'], public['committees'][0]['id']) == ('Malá', 'radiologist', committee.pk)

    r = accept(token)
    assert r.status_code == 201, r.json()
    assert r.cookies['access_token'].value                                 # rovnou přihlášený
    me = r.json()
    assert (me['role'], me['specialty'], me['name'], me['onboarding_done']) == (
        'mdt_viewer', 'radiologist', 'MUDr. Eva Malá', False)
    assert [c['id'] for c in me['committees']] == [committee.pk]
    assert accept(token, username='jina').status_code == 410               # podruhé neplatí
    assert APIClient().get(f'/api/mdt/invitations/public/{token}/').json()['status'] == 'used'
    listed = as_user('predseda').get('/api/mdt/invitations/').json()[0]
    assert (listed['status'], listed['used_by']) == ('used', 'mala')

    client = with_jwt(get_user_model().objects.get(username='mala'))
    assert client.patch('/api/mdt/me/', {'onboarding_done': True}, format='json').json()['onboarding_done'] is True


def test_invitation_validation_expiry_revoke_and_resend(seeded):
    client = as_user('predseda')
    assert client.post('/api/mdt/invitations/', {**INVITE, 'specialty': 'patient'}, format='json').status_code == 400
    assert client.post('/api/mdt/invitations/', {**INVITE, 'last_name': ''}, format='json').status_code == 400
    assert client.post('/api/mdt/invitations/', {**INVITE, 'is_external': True}, format='json').status_code == 400
    assert client.post('/api/mdt/invitations/', {**INVITE, 'committees': [999]}, format='json').status_code == 400

    expired = invite({'send_email': False})
    assert expired['email_sent'] is False
    Invitation.objects.filter(pk=expired['id']).update(expires_at=timezone.now() - timedelta(minutes=1))
    assert APIClient().get(f"/api/mdt/invitations/public/{token_of(expired['link'])}/").status_code == 410

    resent = client.post(f"/api/mdt/invitations/{expired['id']}/resend/", {'send_email': False}, format='json').json()
    assert resent['status'] == 'pending' and resent['link'] != expired['link']
    assert accept(token_of(resent['link'])).status_code == 201
    assert client.post(f"/api/mdt/invitations/{expired['id']}/revoke/").status_code == 409   # použitá

    revoked = invite({'email': ''})
    assert client.post(f"/api/mdt/invitations/{revoked['id']}/revoke/").json()['status'] == 'revoked'
    assert accept(token_of(revoked['link']), username='zruseny').status_code == 410
    assert APIClient().get('/api/mdt/invitations/public/neexistuje/').status_code == 404


def test_external_doctor_invitation(seeded):
    committee = Committee.objects.first()
    created = invite({'is_external': True, 'organization': 'Nemocnice Jih', 'role': 'mdt_doctor',
                      'committees': [committee.pk]})
    assert (created['role'], created['is_external']) == ('mdt_viewer', True)     # externí pacienty nezařazuje
    me = accept(token_of(created['link']), username='externi').json()
    assert (me['role'], me['organization'], me['is_external']) == ('mdt_viewer', 'Nemocnice Jih', True)
    pid = me['practitioner_id']
    role = seeded.store[f'PractitionerRole/{pid}-role']
    assert role['organization'] == {'reference': 'Organization/ORG-NEMOCNICE-JIH', 'display': 'Nemocnice Jih'}
    assert seeded.store['Organization/ORG-NEMOCNICE-JIH']['name'] == 'Nemocnice Jih'


def test_external_doctor_sees_only_invited_sessions(seeded):
    sessions = list(MdtSession.objects.filter(cases__isnull=False).distinct())
    mine, other = sessions[0], next(s for s in sessions if s.committee_id != sessions[0].committee_id)
    created = invite({'is_external': True, 'organization': 'Nemocnice Jih', 'committees': []})
    accept(token_of(created['link']), username='externi')
    user = get_user_model().objects.get(username='externi')
    mine.invited.add(user)                                  # přizvaný jen na jedno zasedání
    client = with_jwt(user)

    assert [s['id'] for s in client.get('/api/mdt/sessions/').json()] == [mine.pk]
    my_case, other_case = mine.cases.first(), other.cases.first()
    assert client.get(f'/api/mdt/sessions/{mine.pk}/').status_code == 200
    assert client.get(f'/api/mdt/sessions/{other.pk}/').status_code == 403
    assert client.get(f'/api/mdt/cases/{my_case.pk}/doctor-rules/').status_code == 200
    assert client.get(f'/api/mdt/cases/{other_case.pk}/doctor-rules/').status_code == 403
    assert client.get(f'/api/mdt/patients/{my_case.patient_fhir_id}/intake/').status_code == 200
    if other_case.patient_fhir_id != my_case.patient_fhir_id:
        assert client.get(f'/api/mdt/patients/{other_case.patient_fhir_id}/intake/').status_code == 403
    assert client.get('/api/patients/').status_code == 403                 # seznam všech pacientů ne
    assert client.get(f'/api/mdt/cases/{my_case.pk}/similar/').status_code == 403
    assert client.get('/api/evidence/?id=KRC-2.4').status_code != 403       # guidelines ano
    assert client.get('/api/mdt/me/').status_code == 200

    mine.excluded.add(user)                                 # vyřazený člen komise: přizvání má přednost
    assert [s['id'] for s in client.get('/api/mdt/sessions/').json()] == [mine.pk]
    mine.invited.remove(user)
    assert client.get('/api/mdt/sessions/').json() == []
    # interní lékař vidí všechno jako dřív
    assert len(with_jwt(get_user_model().objects.get(username='chirurg')).get('/api/mdt/sessions/').json()) \
        == MdtSession.objects.count()


def test_committees_and_session_invited(seeded):
    users = {u.username: u for u in get_user_model().objects.all()}
    assert as_user('onkolog').post('/api/mdt/committees/', {'name': 'Nová'}, format='json').status_code == 403
    created = as_user('predseda').post('/api/mdt/committees/', {
        'name': 'Hrudní komise B', 'members': [users['chirurg'].pk, users['radiolog'].pk]}, format='json')
    assert created.status_code == 201 and len(created.json()['members']) == 2
    cid = created.json()['id']
    assert as_user('predseda').post('/api/mdt/committees/', {'name': 'hrudní komise b'},
                                    format='json').status_code == 400

    session = MdtSession.objects.first()
    r = as_user('predseda').put(f'/api/mdt/sessions/{session.pk}/invited/', {
        'committee_id': cid, 'excluded': [users['radiolog'].pk], 'invited': [users['patolog'].pk]}, format='json')
    assert r.status_code == 200
    assert sorted(a['user_id'] for a in r.json()['attendees']) == sorted([users['chirurg'].pk, users['patolog'].pk])
    assert as_user('chirurg').put(f'/api/mdt/sessions/{session.pk}/invited/', {'invited': []},
                                  format='json').status_code == 403
    assert as_user('chirurg').get(f'/api/mdt/sessions/{session.pk}/').json()['committee']['id'] == cid

    patched = as_user('predseda').patch(f'/api/mdt/committees/{cid}/', {'members': [users['onkolog'].pk]},
                                        format='json').json()
    assert [m['user_id'] for m in patched['members']] == [users['onkolog'].pk]
    assert as_user('predseda').delete(f'/api/mdt/committees/{cid}/').status_code == 204
    session.refresh_from_db()
    assert session.committee_id is None


def test_manager_edits_accounts(seeded):
    users = {u.username: u for u in get_user_model().objects.all()}
    client = as_user('predseda')
    url = f"/api/mdt/users/{users['radiolog'].pk}/"
    assert client.patch(url, {'is_external': True}, format='json').status_code == 400     # bez nemocnice
    me = client.patch(url, {'is_external': True, 'organization': 'FN Sever', 'is_manager': True}, format='json').json()
    assert (me['is_external'], me['organization'], me['is_manager']) == (True, 'FN Sever', True)
    assert client.patch(url, {'role': 'mdt_doctor'}, format='json').status_code == 400     # externí = člen komise
    assert client.patch(url, {'is_active': False}, format='json').json()['is_active'] is False
    assert 'radiolog' not in [u['username'] for u in client.get('/api/mdt/users/').json()]
    assert 'radiolog' in [u['username'] for u in client.get('/api/mdt/users/?all=1').json()]
    own = f"/api/mdt/users/{users['predseda'].pk}/"
    assert client.patch(own, {'is_manager': False}, format='json').status_code == 400
    assert client.patch(own, {'is_active': False}, format='json').status_code == 400


def test_seed_assigns_committees(seeded):
    assert not MdtSession.objects.filter(committee__isnull=True).exists()
    committee = MdtSession.objects.first().committee
    assert committee.name == MdtSession.objects.first().title
    assert committee.members.filter(username='onkolog').exists()
    call_command('seed_mdt')                                  # idempotentní
    assert Committee.objects.count() == MdtSession.objects.values('title').distinct().count()
    assert MdtCase.objects.count()


def test_live_respects_invitations(seeded):
    """Živě na MDT (T-354) + pozvaní (T-362): externí lékař vidí jen své zasedání, pozvaný má důvod `invited`."""
    sessions = list(MdtSession.objects.all()[:2])
    MdtSession.objects.filter(pk__in=[s.pk for s in sessions]).update(status='in_progress')
    created = invite({'is_external': True, 'organization': 'Nemocnice Jih', 'committees': []})
    accept(token_of(created['link']), username='externi')
    user = get_user_model().objects.get(username='externi')
    sessions[0].invited.add(user)
    live = with_jwt(user).get('/api/mdt/live/').json()
    assert [s['id'] for s in live['sessions']] == [sessions[0].pk]
    assert 'invited' in live['sessions'][0]['reasons']
    assert with_jwt(user).get(f'/api/mdt/sessions/{sessions[1].pk}/live/').status_code == 403
    assert with_jwt(user).get(f'/api/mdt/sessions/{sessions[0].pk}/live/').status_code == 200
