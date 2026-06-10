# lottoBot
lotto bot 

## Render environment variables

Set these variables in Render before deploying:

- `TELEGRAM_API_TOKEN` - Telegram bot token.
- `ADMIN_IDS` - comma-separated Telegram user IDs that can generate unlimited lottery results without paying.
- `PAYPAL_CLIENT_ID` - PayPal REST app client ID.
- `PAYPAL_CLIENT_SECRET` - PayPal REST app secret.
- `PAYPAL_PLAN_ID` - PayPal subscription plan ID. Defaults to the current hard-coded plan if omitted.
- `PAYPAL_MODE` - `live` for production or `sandbox` for testing. Defaults to `live`.
- `PUBLIC_BASE_URL` - public Render service URL, for example `https://your-service.onrender.com`.
- `BOT_USERNAME` - Telegram bot username without `@`; used for referral links.

PayPal webhooks should be pointed to:

`https://your-service.onrender.com/webhook/paypal`

The bot creates a personal PayPal subscription link per Telegram user, stores the Telegram ID in PayPal `custom_id`, and unlocks unlimited VIP generations when the subscription is activated.
