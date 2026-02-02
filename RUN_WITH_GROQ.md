# Run with Groq (free AI)

## Set your API key

Get a free key at [console.groq.com/keys](https://console.groq.com/keys).

**PowerShell (same terminal before `python app.py`):**
```powershell
$env:GROQ_API_KEY = "gsk_your_key_here"
python app.py
```

**Or use a .env file** (works from IDE too):
1. Create a file named `.env` in the project folder.
2. Add: `GROQ_API_KEY=gsk_your_key_here`
3. Install: `pip install python-dotenv`
4. Run: `python app.py`

You should see: `[OK] Groq API initialized (free tier)` and `[INFO] AI (Groq): Yes`.
