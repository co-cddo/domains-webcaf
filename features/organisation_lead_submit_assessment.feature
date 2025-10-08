Feature: Organisation lead can submit assessment

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
#    Database does not store the passwords
    And the user "other@example.gov.uk" exists
    And User "other@example.gov.uk" has the profile "Organisation lead" assigned in "Ministry of Agriculture"
    And the application is running
    And there is a "enhanced" profile assessment  for "System 1", "Ministry of Agriculture", for the period "25/26" in "draft" status and data "alice_completed_assessment.json"
    And the user logs in with username  "other@example.gov.uk" and password "password"

  Scenario: Organisation lead can can submit a completed assessment
    Given Think time 1 seconds
    Then they should see page title "My account - other - Complete a WebCAF self-assessment - GOV.UK"
    And click link with text "View 1 draft self-assessment"
    And click link in table row containing value "System 1" with text "View"
    And click link with text "Complete the full self-assessment"
    And click button with text "Save and send for review"
    # This will check the information stored for the current assessment
    # matches the information displayed on the confirmation page as well
    # as confirming the assessment is in submitted stage.
    And confirm current assessment is in "submitted" state
