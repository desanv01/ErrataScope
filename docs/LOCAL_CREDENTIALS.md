# Project-local Nebius key

The W01 CLI now explicitly loads `C:\Users\Dv\Desktop\ErrataScope\.env.local`. Windows account-wide configuration is optional. DeepSeek keeps its existing coding-model configuration.

1. Copy `.env.example` to `.env.local` in the project root using your editor/file manager. Do not overwrite an existing file.
2. In your local editor set `NEBIUS_API_KEY=your_actual_key`. Use the actual Token Factory API key, not a promo code, without `Bearer` or spaces. Never paste it into agent chat.
3. Save as UTF-8 without a `.txt` extension. Existing `.gitignore` excludes this file. It is local plaintext, not an encrypted vault.
4. Through the worker terminal run:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py check-key
```

This prints CONFIGURED or MISSING with no request or provider-ledger change. It does not prove balance/authentication/model access. No restart is needed for the next CLI invocation to reread the file. A nonempty process NEBIUS_API_KEY takes precedence; remove/update any stale account-wide value and restart the app, or deliberately clear it in the invoking shell to use the file.

Only this application's explicit loader reads the file; `.env.local` is not automatically a universal desktop-harness setting. Workers should execute the check command rather than opening/catting it. Supported syntax: one key assignment, optional matching quotes, blank lines/comments, no multiline values or variable expansion. Unrelated variables are ignored.

**Current next step:** credits are now available. Configure the key, verify presence, then use [W01 live-completion v2](execution/prompts/W01-LIVE-COMPLETION-V2.md). W02 is prepared and follows W01 acceptance. Do not run superseded prompts or launch two workers in the shared folder.
