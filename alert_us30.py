name: US30 Macro Alert
on:
  schedule:
    - cron: '*/30 13-21 * * 1-5'
  workflow_dispatch:
jobs:
  run-script:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install requests zoneinfo playwright
          # On force l'installation dans le dossier local
          playwright install chromium --with-deps

      - name: Run script
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          # On indique au script où chercher le navigateur
          PLAYWRIGHT_BROWSERS_PATH: 0
        run: python alert_us30.py
