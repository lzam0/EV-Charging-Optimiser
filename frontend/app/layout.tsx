import type {Metadata} from 'next';
import {Inter} from 'next/font/google';
import './globals.css';
import {AppThemeProvider} from './providers';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'EV Charging Optimiser',
  description: 'The cheapest and greenest time to charge your EV.',
};

export default function RootLayout({children}: LayoutProps<'/'>) {
  return (
    <html lang="en" className={inter.variable} data-theme="light">
      <body>
        <AppThemeProvider>{children}</AppThemeProvider>
      </body>
    </html>
  );
}
