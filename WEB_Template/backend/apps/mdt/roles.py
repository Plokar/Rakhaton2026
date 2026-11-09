"""Role a demo účty (D-014, ARCH §6.2, POZADAVKY_LEKARE §1)."""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.models import Group

from .models import UserProfile

ADMIN, DOCTOR, VIEWER = 'mdt_admin', 'mdt_doctor', 'mdt_viewer'
ROLES = (ADMIN, DOCTOR, VIEWER)

# účet → (skupina, odbornost RoleId, celé jméno)
DEMO_USERS = {
    'predseda': (ADMIN, 'oncologist', 'Předseda komise (klinický onkolog)'),
    'onkolog': (DOCTOR, 'oncologist', 'Klinický onkolog'),
    'pneumolog': (DOCTOR, 'pulmonologist', 'Pneumolog'),
    # další zadávající lékaři pro nové pacienty a import víc pacientů (T-335)
    'onkolog-git': (DOCTOR, 'oncologist', 'Klinický onkolog (GIT)'),
    'paliatr': (DOCTOR, 'palliative_care', 'Lékař paliativní péče'),
    'chirurg': (VIEWER, 'surgeon', 'Chirurg'),
    'radiolog': (VIEWER, 'radiologist', 'Radiolog'),
    'patolog': (VIEWER, 'pathologist', 'Patolog'),
    'radioterapeut': (VIEWER, 'radiation_oncologist', 'Radiační onkolog'),
}
# zadávající lékař podle pacienta (ARCH §6.2): P04 a hrudní demo pacienti pneumolog, GIT demo pacienti
# onkolog-git (data/demo_pacienti), ostatní onkolog
REQUESTER_BY_PATIENT = {'P04': 'pneumolog',
                        **{f'P{n}': 'pneumolog' for n in (*range(13, 17), 41, 42, 43, 56, 57)},
                        **{f'P{n}': 'onkolog-git' for n in (*range(21, 25), 39, 40, 52, 69, 70)}}
DEFAULT_REQUESTER = 'onkolog'


def display_name(user) -> str:
    """Jméno lékaře s tituly („MUDr. Petr Novák, Ph.D.“, T-338); bez jména uživatelské jméno."""
    name = user.get_full_name() or user.username
    try:
        profile = user.mdt_profile
    except UserProfile.DoesNotExist:
        return name
    before, after = profile.title_before.strip(), profile.title_after.strip()
    return f"{before + ' ' if before else ''}{name}{', ' + after if after else ''}"


def role(user) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return ADMIN
    names = set(user.groups.values_list('name', flat=True))
    return next((r for r in ROLES if r in names), VIEWER)


# odbornost lékaře = RoleId (ARCH §8.1) bez „hlasu pacienta“
SPECIALTIES = ('oncologist', 'surgeon', 'radiation_oncologist', 'radiologist', 'pathologist', 'pulmonologist',
               'cardiologist', 'nuclear_medicine', 'palliative_care', 'geriatrician', 'geneticist', 'coordinator')


def specialty(user) -> str | None:
    profile = UserProfile.objects.filter(user=user).first()
    return profile.specialty if profile and profile.specialty else None


def assign(user, *, role: str | None = None, specialty: str | None = None) -> None:
    """Role (právě jedna skupina MDT) a odbornost uživatele (T-319). `None` = beze změny."""
    if role is not None:
        user.groups.remove(*Group.objects.filter(name__in=ROLES))
        user.groups.add(Group.objects.get_or_create(name=role)[0])
    if specialty is not None:
        UserProfile.objects.update_or_create(user=user, defaults={'specialty': specialty})


def practitioner_id(user) -> str | None:
    """Lékař v IRIS, se kterým je účet propojený (T-328): podle něj se hledají „moje úkoly“."""
    profile = UserProfile.objects.filter(user=user).first()
    return profile.practitioner_fhir_id if profile and profile.practitioner_fhir_id else None


def ensure_practitioner(user) -> str:
    """Propojí účet s lékařem v IRIS; když propojený není, založí `Practitioner/LEK-APP-<účet>` (idempotentní PUT)."""
    from services import practitioners
    from services.fhir import client as fhir

    profile, _ = UserProfile.objects.get_or_create(user=user)
    pid = profile.practitioner_fhir_id or practitioners.app_practitioner_id(user.username)
    if pid.startswith(practitioners.APP_PREFIX):        # lékaře účtu aplikace udržujeme (jméno, odbornost)
        fhir.put(practitioners.app_practitioner(pid, display_name(user), profile.specialty,
                                                user.username))
    if profile.practitioner_fhir_id != pid:
        profile.practitioner_fhir_id = pid
        profile.save(update_fields=['practitioner_fhir_id'])
    return pid


def users_by_practitioner() -> dict[str, dict]:
    """Lékař v IRIS → účet aplikace (`{user_id, username}`) pro adresář lékařů."""
    return {p.practitioner_fhir_id: {'user_id': p.user_id, 'username': p.user.username}
            for p in UserProfile.objects.exclude(practitioner_fhir_id='').select_related('user')}


DEV_DEMO_PASSWORD = 'demo123456'
# výchozí heslo z repa a zástupné hodnoty z `.env.prod.example` nesmí do pilotu ani produkce
WEAK_DEMO_PASSWORDS = {DEV_DEMO_PASSWORD, 'CHANGE-ME-DEMO-PASSWORD', ''}


def demo_password() -> str:
    """Heslo demo účtů: `MDT_DEMO_PASSWORD`. V pilotu a produkci (`MDT_STRICT_SECRETS`, settings_prod) musí být
    nastavené, alespoň 12 znaků a ne výchozí z repa; v dev a testech platí výchozí `demo123456`."""
    strict = getattr(settings, 'MDT_STRICT_SECRETS', False)
    password = os.environ.get('MDT_DEMO_PASSWORD', '' if strict else DEV_DEMO_PASSWORD)
    if strict and (password in WEAK_DEMO_PASSWORDS or len(password) < 12):
        raise ImproperlyConfigured(
            'MDT_DEMO_PASSWORD: v pilotu a produkci nastavte vlastní heslo demo účtů (aspoň 12 znaků, ne výchozí z repa).')
    return password


def ensure_demo_users(reset_passwords: bool = False) -> dict:
    """Skupiny + demo účty (heslo `MDT_DEMO_PASSWORD`). Idempotentní; heslo existujícího účtu změní jen `reset_passwords`."""
    groups = {name: Group.objects.get_or_create(name=name)[0] for name in ROLES}
    password = demo_password()
    users = {}
    for username, (group, spec, full_name) in DEMO_USERS.items():
        user, created = get_user_model().objects.get_or_create(
            username=username, defaults={'first_name': full_name, 'email': f'{username}@mdt.local'})
        if created or reset_passwords:
            user.set_password(password)
            user.save()
        user.groups.add(groups[group])
        UserProfile.objects.update_or_create(user=user, defaults={'specialty': spec})
        users[username] = user
    return users
