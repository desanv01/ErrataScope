async (page) => {
  await page.waitForTimeout(2000);
  await page.locator('.claim').filter({hasText:'DBGMCU_IDCODE register value remains the same'}).getByRole('button').first().click();
  await page.waitForTimeout(6500);
  await page.locator('.claim').filter({hasText:'Source Identity'}).getByRole('button').first().click();
  await page.waitForTimeout(6000);
  await page.getByRole('button',{name:'2.2.18 Incorrect reset behavior when using NRST pin',exact:true}).click();
  await page.locator('.claim').filter({hasText:'The system may fail'}).getByRole('button').first().click();
  await page.waitForTimeout(6500);
}
