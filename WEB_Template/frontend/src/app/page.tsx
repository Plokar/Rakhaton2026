import { redirect } from 'next/navigation';

// MDTcore nemá veřejnou landing page: rovnou na přehled, nepřihlášené pošle proxy.ts na /login.
export default function HomePage() {
  redirect('/dashboard');
}
