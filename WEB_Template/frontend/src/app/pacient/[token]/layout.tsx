import type { Metadata } from 'next';

// T-384: stránka s odkazem pro pacienta se nesmí indexovat ani posílat adresu (token) dál v Referer
export const metadata: Metadata = {
  title: 'Shrnutí z onkologické komise',
  robots: { index: false, follow: false },
  referrer: 'no-referrer',
};

export default function PatientLinkLayout({ children }: { children: React.ReactNode }) {
  return children;
}
