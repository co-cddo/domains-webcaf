@webcaf @ui @assessment @documentation
# Purpose: Validate that an organisation user can log in and view a draft WebCAF assessment
# Audience: Test engineers and developers maintaining the WebCAF UI flows
# Scope: UI journey from login -> My account -> Draft assessments -> Draft assessment overview
# Preconditions:
#  - The application must be running and accessible (step: "Given the application is running")
#  - Seed data is created via Background: Organisation, User, Profile, and a started assessment for "System 1"
# Test data used in this file:
#  - Organisation: "Ministry of Agriculture" (type: ministerial-department)
#  - Systems: System 1, System 2, System 3
#  - User: organisation_user@example.gov.uk (role: Organisation user)
#  - Password: "password" (stubbed for test purposes) # pragma: allowlist secret
# Execution notes:
#  - "Think time" steps are used to pace UI actions in slower environments.
#  - DOM assertions rely on specific selectors (e.g., td[data-label], govuk heading classes) – update if templates change.
# Maintenance notes:
#  - Do not change step phrasing unless corresponding step definitions are updated. In particular, keep the
#    exact wording for link-click steps present below as they are bound to existing step definitions.

Feature: User assessment completion steps

  # Background seeds organisation, user, profile and an in-progress assessment for System 1
  Background:
    Given Organisation Ministry of Agriculture of type ministerial-department exists with systems System 1, System 2, System 3
#    Database does not store the passwords
    And the user organisation_user@example.gov.uk exists
    And User organisation_user@example.gov.uk has the profile Organisation user assigned in Ministry of Agriculture
    And Organisation Ministry of Agriculture has started an assessment for the system System 1


  # Scenario: User logs in, navigates to Draft assessments, and verifies key fields on the draft assessment
  Scenario: Valid user logs in and view the assessment
    Given the application is running
      # Allow front-end to fully load and settle before login
    And Think time 5 seconds
    When the user logs in with username organisation_user@example.gov.uk and password password
      # Confirms successful login and landing page
    Then they should see page title My account - organisation_user
      # Confirms presence of draft assessment summary
    And page contains text View 1 draft assessment(s) in paragraph
      # Intentionally spelled as in bound step definition; do not change "clck"
    Then clck the link with the text View 1 draft assessment(s)
      # Validates the table shows the expected system
    And confirm element td[data-label="System name"] with the text System 1 exists
      # Validates the assessment profile shown is "Baseline"
    And confirm element td[data-label="CAF profile"] with the text Baseline exists
      # Intentionally spelled as in bound step definition; do not change "clck"
    Then clck the link with the text View
      # Confirms user is on the assessment overview page
    And confirm element h1.govuk-heading-l with the text Submit a WebCAF self-assessment exists
      # Confirm the first two lines of the table to have the completed against them
    And confirm element li.govuk-task-list__item--with-link:nth-of-type(1)  with the text Choose your government CAF profile Completed exists
    And confirm element li.govuk-task-list__item--with-link:nth-of-type(2)  with the text Provide system details Completed exists
