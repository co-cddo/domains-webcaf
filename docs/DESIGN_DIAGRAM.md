### WebCAF domain relationships: Assessment, UserProfile, Review (with context)

This README explains how the core domain entities relate to each other and provides diagrams you can render with Mermaid. It reflects the current code in `webcaf/webcaf/models.py` and the admin configuration in `webcaf/webcaf/admin.py`.


---

### Scope and purpose
- Assessment: captures a CAF self-assessment for a given `System` and assessment period, including JSON content and completion helpers.
- UserProfile: associates a `User` with an `Organisation` and a role (`cyber_advisor`, `organisation_lead`, `organisation_user`, `assessor`, `reviewer`).
- Review: records assurance review metadata and structured review content; tracks who last updated the review via `last_updated_by`.
- Tip: a Targeted Improvement Plan (TIP) created when a `Review` is finalised. It tracks how the organisation plans to action the review's recommendations, storing structured action data in `tip_data` and moving through its own status lifecycle (to do → in progress → answers confirmed → review → approved/rejected → closed).

Context models (referenced for relationships): `Organisation`, `System`, `User`.

---

### High-level relationships
- Organisation 1—M System
- System 1—M Assessment
- Assessment 1—1 Review (one review per assessment)
- User 1—M UserProfile (each profile may be tied to an Organisation)
- UserProfile M—1 Organisation
- Review 1—1 Tip (one Tip per review)

Key constraints from the current models:
- Review: `unique_together = (assessment,)` — at most one review per assessment. `last_updated_by` is an optional FK to `User` for audit.
- Assessment: `unique_together = (assessment_period, system, status)` — ensures unique assessment combinations.
- Tip: `review` is a `OneToOneField` to `Review` (with `unique_together = (review,)`) — at most one Tip per review; deleting the review cascades to delete the Tip. `last_updated_by` is an optional FK to `User` for audit. The model defines custom permissions `can_approve_tip` and `can_reject_tip`. A Tip is created via `Review.finalise_review()` (`Tip.objects.get_or_create(review=self)`).

---

### Class diagram (Mermaid)
```mermaid
classDiagram
  class Organisation {
    +id: int
    +name: str
    +reference: str?
  }
  class System {
    +id: int
    +name: str
    +reference: str?
  }
  class Assessment {
    +id: int
    +reference: str?
    +status: choice
    +framework: choice
    +caf_profile: choice
    +assessment_period: str
    +created_on: datetime
    +last_updated: datetime
    +submission_due_date: datetime?
    +assessments_data: JSON
    +review_type: choice
  }
  class Review {
    +id: int
    +created_on: datetime
    +last_updated: datetime
    +status: choice
    +review_data: JSON
    +reference: str?
  }
  class User {
    +id: int
    +email: email
    +first_name: str
    +last_name: str
  }
  class UserProfile {
    +id: int
    +role: choice?
  }
  class Tip {
    +id: int
    +created_on: datetime
    +last_updated: datetime
    +status: choice
    +tip_data: JSON
    +reference: str?
  }

  Organisation "1" -- "*" System : owns
  System "1" -- "*" Assessment : has
  Assessment "1" -- "1" Review : has
  Review "1" -- "1" Tip : has
  User "1" -- "*" UserProfile : has
  UserProfile "*" -- "1" Organisation : belongs to
  Review "1" -- "0..1" User : last_updated_by
  Tip "1" -- "0..1" User : last_updated_by
  Assessment "1" -- "0..1" User : created_by
  Assessment "1" -- "0..1" User : last_updated_by
```

---

### ER diagram (Mermaid)
```mermaid
erDiagram
  ORGANISATION ||--o{ SYSTEM : owns
  SYSTEM ||--o{ ASSESSMENT : has
  ASSESSMENT ||--|| REVIEW : has
  REVIEW ||--|| TIP : has
  USER ||--o{ USERPROFILE : has
  ORGANISATION ||--o{ USERPROFILE : includes
  USER ||--o{ ASSESSMENT : created_by
  USER ||--o{ ASSESSMENT : last_updated_by
  USER ||--o{ REVIEW : last_updated_by
  USER ||--o{ TIP : last_updated_by

  ORGANISATION {
    int id PK
    string name UK
    string reference UK
  }

  SYSTEM {
    int id PK
    int organisation_id FK
    string name
    string reference UK
  }

  ASSESSMENT {
    int id PK
    int system_id FK
    string reference UK
    string assessment_period
    string status
  }

  REVIEW {
    int id PK
    int assessment_id FK
    int last_updated_by_id FK
    string status
    json review_data
    string reference UK
  }

  TIP {
    int id PK
    int review_id FK
    int last_updated_by_id FK
    string status
    json tip_data
    string reference UK
  }

  USER {
    int id PK
    string email
  }

  USERPROFILE {
    int id PK
    int user_id FK
    int organisation_id FK
    string role
  }
```

---

### How to view diagrams
- Many Markdown renderers support Mermaid. If your viewer does not, paste the blocks at https://mermaid.live

---

### Quick navigation and examples
- From a `System` instance: `system.assessments.all()`
- From an `Assessment` instance (one review per assessment): `assessment.reviews.first()` or access via the reviews related manager
- Find reviews last updated by a user: `Review.objects.filter(last_updated_by=user)`
- Find assessment for a review: `review.assessment`
- Find the Tip (Targeted Improvement Plan) for a review: `review.tip`
- Find the review a Tip belongs to: `tip.review`
- Find organisation for an assessment: `assessment.system.organisation`
- Find user profiles in an organisation: `organisation.members.all()`
