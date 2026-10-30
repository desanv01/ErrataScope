async (page) => {
  const note = page.getByRole('textbox',{name:/Review note Required/});
  await note.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1800);
  await note.pressSequentially('Checked the cited NRST source. Device identity and exception remain unresolved. This review does not establish applicability.', {delay:38});
  await page.waitForTimeout(3000);
  await page.getByRole('button',{name:'Review draft',exact:true}).click();
  await page.getByText('Checked the cited NRST source. Device identity and exception remain unresolved. This review does not establish applicability.',{exact:true}).waitFor();
  await page.waitForTimeout(6500);
}
