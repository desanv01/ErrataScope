async (page) => {
  await page.getByRole('region',{name:'Unresolved information',exact:true}).scrollIntoViewIfNeeded();
  await page.waitForTimeout(7000);
  await page.getByRole('region',{name:'Coverage status',exact:true}).scrollIntoViewIfNeeded();
  await page.waitForTimeout(5000);
  await page.getByText('Unselected entries',{exact:true}).click();
  await page.waitForTimeout(5000);
}
