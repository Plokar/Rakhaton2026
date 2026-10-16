/**
 * Fixtures demo pacienta P03 pro vývoj UI bez backendu (ARCHITEKTURA §7.3, T-009).
 *
 * Kanonické soubory jsou v data/fixtures/ (validuje je pydantic v testech backendu).
 * src/fixtures/ je jejich kopie, protože frontend kontejner ani Vercel nevidí složky mimo
 * WEB_Template/frontend. Shodu kopie hlídá backend test test_frontend_copy_is_identical.
 */
import type { Brief, Decision, IntakePrefill } from '@/types/mdt';
import briefJson from '@/fixtures/brief_P03.json';
import decisionJson from '@/fixtures/decision_P03.json';
import intakeJson from '@/fixtures/intake_P03.json';

// JSON import má široké typy (string místo literálů), proto přetypování; strukturu hlídá pydantic.
export const briefP03 = briefJson as Brief;
export const decisionP03 = decisionJson as Decision;
export const intakeP03 = intakeJson as IntakePrefill;
