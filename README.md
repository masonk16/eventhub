# EventHub

A free, central hub for event info. Anyone can post; promoters prove they run an event to earn a **Verified organizer** badge.

## Run it

    docker compose up -d                 # PostgreSQL (or point .env at your own server)
    cp .env.example .env
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python manage.py makemigrations accounts events
    python manage.py migrate
    python manage.py seed_categories
    python manage.py setup_roles
    python manage.py createsuperuser
    python manage.py runserver
    python manage.py test                # the Postgres user needs CREATEDB

## Layout

- `accounts/` custom `User` (attendee, promoter, moderator), `PromoterProfile`, signup, `@promoter_required`
- `events/` events, categories, ownership verification, admin review
- `templates/` every template, Tabler-based (loaded from CDN)

## User types

| Type | Can do |
|------|--------|
| Attendee | Browse and filter events |
| Promoter | Post, edit, delete and verify their own events |
| Moderator | Staff access to review verification requests in `/admin/` |

Signup offers attendee or promoter only. Set moderators in the admin (User type). Staff access follows the type.

## Verification

| Method  | Proof |
|---------|-------|
| Website | Promoter publishes `eventhub-verify=<code>` on their site or ticket page; we fetch it. On shared platforms it must be the exact page listed. |
| Email   | Signed link emailed to an address on the official website's domain (free-mail and shared domains refused). Expires in 3 days. |
| Manual  | Evidence submitted; a moderator approves in admin. |

Changing the website or ticket link on a verified event clears verification.

## Before going live

- Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, a real email backend and `STATIC_ROOT`.
- Add rate limiting, email confirmation at signup, and a "report this listing" flow.
- Self-host Tabler's CSS/JS if you don't want a CDN dependency.
