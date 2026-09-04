import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import puppeteer from 'puppeteer-core';

const channel = (process.env.TELEGRAM_CHANNEL || 'ictfromabc28').replace(/^@/, '');
const reportPath = process.env.TELEGRAM_PROBE_REPORT || '/tmp/telegram-probe.json';

function findChrome() {
  if (process.env.PUPPETEER_EXECUTABLE_PATH) return process.env.PUPPETEER_EXECUTABLE_PATH;
  for (const binary of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    try {
      return execFileSync('which', [binary], { encoding: 'utf8' }).trim();
    } catch {}
  }
  return null;
}

const executablePath = findChrome();
if (!executablePath) {
  console.warn('Telegram probe skipped: Chrome/Chromium executable not found.');
  fs.writeFileSync(reportPath, JSON.stringify({ channel, skipped: true, reason: 'chrome-not-found', posts: [] }, null, 2));
  process.exit(0);
}

const browser = await puppeteer.launch({
  executablePath,
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 1800 });
  await page.setUserAgent(
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36'
  );

  const url = `https://t.me/s/${encodeURIComponent(channel)}`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForNetworkIdle({ idleTime: 700, timeout: 10000 }).catch(() => {});

  const report = await page.evaluate((channelName) => {
    const items = [...document.querySelectorAll('.tgme_widget_message')];
    const posts = items.map((node) => {
      const dataPost = node.getAttribute('data-post') || '';
      const idMatch = dataPost.match(/\/(\d+)$/);
      const text = node.querySelector('.tgme_widget_message_text')?.innerText?.trim() || '';
      const documentTitle = node.querySelector('.tgme_widget_message_document_title')?.textContent?.trim() || '';
      const datetime = node.querySelector('time')?.getAttribute('datetime') || '';
      const postUrl = node.querySelector('.tgme_widget_message_date')?.href || '';
      const combined = `${documentTitle}\n${text}`;
      const quizMatch = combined.match(/\b(?:2028\s*)?quiz[\s_-]*0*(\d{1,3})\b/i);
      return {
        id: idMatch ? Number(idMatch[1]) : null,
        dataPost,
        datetime,
        postUrl,
        documentTitle,
        text,
        quiz: quizMatch ? Number(quizMatch[1]) : null,
        marking: /\bmarking\b/i.test(combined),
      };
    }).filter((post) => post.quiz !== null || /\.pdf$/i.test(post.documentTitle));

    return {
      channel: channelName,
      title: document.title,
      messageCount: items.length,
      posts,
    };
  }, channel);

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`Puppeteer Telegram preview: ${report.messageCount} messages, ${report.posts.length} quiz/PDF candidates.`);
  for (const post of report.posts.slice(-12)) {
    console.log(`  post=${post.id ?? '?'} quiz=${post.quiz ?? '?'} marking=${post.marking} file=${post.documentTitle || '(no title)'}`);
  }
} catch (error) {
  console.warn(`Telegram public-preview probe failed non-fatally: ${error.message}`);
  fs.writeFileSync(reportPath, JSON.stringify({ channel, error: error.message, posts: [] }, null, 2));
} finally {
  await browser.close();
}
