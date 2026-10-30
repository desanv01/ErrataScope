async (page) => {
  await page.getByRole('combobox',{name:'Choose demonstration case'}).selectOption({label:'Synthetic / offline example'});
  await page.getByRole('heading',{name:/Unknown document/}).waitFor();
  await page.waitForTimeout(6500);
  await page.getByRole('region',{name:'Unresolved information',exact:true}).scrollIntoViewIfNeeded();
  await page.waitForTimeout(6500);
  await page.getByRole('region',{name:'Provenance',exact:true}).scrollIntoViewIfNeeded();
  await page.waitForTimeout(5500);
}
