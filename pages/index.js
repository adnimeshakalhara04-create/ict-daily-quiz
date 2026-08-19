import Head from 'next/head';
import Script from 'next/script';

export default function Home() {
  return (
    <>
      <Head>
        <title>ICT Daily Quiz — 2028 Quiz Studio</title>
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <meta name="theme-color" content="#061226" />
        <link rel="stylesheet" href="/styles.css" />
      </Head>
      <div id="app" />
      <div id="modal" />
      <Script src="/app.js" strategy="afterInteractive" />
    </>
  );
}
