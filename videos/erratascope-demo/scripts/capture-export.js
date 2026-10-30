async (page) => {
  await page.waitForTimeout(2500);
  const first = page.waitForEvent('download');
  await page.getByRole('button',{name:'Export JSON',exact:true}).click();
  await (await first).saveAs('videos/erratascope-demo/assets/capture/review-summary.json');
  await page.waitForTimeout(4500);
  const second = page.waitForEvent('download');
  await page.getByRole('button',{name:'Export Markdown',exact:true}).click();
  await (await second).saveAs('videos/erratascope-demo/assets/capture/review-summary.md');
  await page.waitForTimeout(4500);
}
