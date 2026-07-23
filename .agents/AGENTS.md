# Architectural Constraints for AI Support Platform

## Rate Limiting
- DO NOT implement custom Redis rate limiting (`check_rate_limit()`).
- Redis should only be used for response caching, Celery broker/result backend, and Pub/Sub.

## Ticket Management
- DO NOT implement hard deletion of tickets.
- Closing a ticket must be done by updating its status (e.g., `Closed`).
- Any ticket delete endpoint (`DELETE /tickets/{id}`) must be restricted to Admins only.

## Attachments
- DO NOT create a dedicated endpoint for listing attachments (e.g. no `GET /tickets/{id}/attachments`).
- Attachment information must be returned inline as part of the ticket details endpoint (`GET /tickets/{id}`).

## Celery
- Celery MUST ONLY be used for AI-related background tasks:
  - Ticket Classification
  - Priority Prediction
  - AI Summary
  - AI Reply Suggestion
- DO NOT implement email notification background tasks.

## User Roles
- Keep ONLY these roles:
  - `Customer`
  - `Agent`
  - `Admin`
- DO NOT introduce any additional roles.

## Ticket Listing
- DO NOT implement full-text or advanced search.
- Support filtering ONLY by the following fields:
  - `status`
  - `priority`
  - `category`
  - `assigned_agent`
