# Session Management Sequence Diagram

This diagram captures the interactions between Django middlewares and views for detecting session inactivity (30 minutes), recording last accessed time, handling session expiry, and integrating with OIDC logout.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant B as Browser
    participant DJ as Django
    participant SED as Session Expiration Detector MW
    participant LATM as Last Accessed Time MW
    participant V as Secured View
    participant SEV as Session Expired View
    participant IDX as Index View
    participant OIDC as OIDC Provider
    database DB as LastAccessedTime (id, accessed_time, useremail)

    rect rgb(245,245,245)
    note over DJ: Request to a secured endpoint (requires login)
    U->>B: Click link /secured
    B->>DJ: GET /secured
    DJ->>SED: process_request()
    alt Path is NOT secured
        SED-->>DJ: allow
        DJ->>LATM: process_request()
        LATM-->>DJ: allow (no-op if not secured or not logged in)
        DJ->>V: dispatch()
        V-->>DJ: 200 OK
        DJ-->>B: Response
    else Path IS secured
        alt User not authenticated
            SED-->>DJ: allow (login flow handled elsewhere)
            DJ->>LATM: process_request()
            LATM-->>DJ: allow (not logged in)
            DJ->>V: dispatch()
            V-->>DJ: 302 to login (handled by auth)
            DJ-->>B: 302 Redirect
        else User authenticated
            SED->>DB: Get LastAccessedTime by useremail
            alt Record exists and now - accessed_time <= 30m
                SED-->>DJ: allow
                DJ->>LATM: process_request()
                alt Secured path AND user logged in
                    LATM->>DB: Upsert accessed_time = now
                    LATM-->>DJ: allow
                else Otherwise
                    LATM-->>DJ: allow (no-op)
                end
                DJ->>V: dispatch()
                V-->>DJ: 200 OK
                DJ-->>B: Response
            else No record OR inactivity > 30m
                SED-->>DJ: 302 Redirect to /session-expired
                DJ-->>B: 302 Redirect
                B->>DJ: GET /session-expired
                DJ->>SEV: render()
                note right of SEV: Show message: inactive for 30 minutes.<br/>Provide link: http://<oidc server>/sign-out?to_client=<client id>
                SEV-->>B: 200 OK (HTML)
                U->>B: Click OIDC sign-out link
                B->>OIDC: GET /sign-out?to_client=<client id>
                OIDC-->>B: 302 Redirect back to Index
                B->>DJ: GET /
                DJ->>IDX: render()
                note right of IDX: Check HTTP Referer is OIDC sign-out URL.<br/>If a user is present in session, update LastAccessedTime to now.
                IDX->>DB: (Conditional) Upsert accessed_time = now
                IDX-->>B: 200 OK (Index)
            end
        end
    end
    end
```

Notes
- "Secured path" means URLs where the user must be logged in. Non-secured paths bypass the inactivity check and last-accessed updates.
- LastAccessedTime model fields: id, accessed_time (datetime), useremail (string).
- The Session Expiration Detector middleware is responsible solely for deciding if inactivity > 30 minutes and redirecting to the Session Expired view.
- The Last Accessed Time middleware is responsible for updating the timestamp for logged-in users on secured paths.
- The Index view should verify that the referrer is the OIDC sign-out URL before updating last accessed time.
- The OIDC sign-out link shape: http://<oidc server>/sign-out?to_client=<client id>.
