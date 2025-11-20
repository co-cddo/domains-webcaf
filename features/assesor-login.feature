Feature: Assessor can log in and view assessments


  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
    And the user "test_assessor@example.com" exists
    And the application is running
    And cookies have been "accepted"
    And User "test_assessor@example.com" has the profile "Independent assessor" assigned in "Ministry of Agriculture"
    And there is an assessor registered in the system named "Test Assessor company"
    And the "Test Assessor company" is assigned to "Ministry of Agriculture"
    And the user "test_assessor@example.com" belongs to the assessor "Test Assessor company"


  Scenario: Assessor can log in and see their account page
    Given Think time 1 seconds
    And the user logs in with username  "test_assessor@example.com" and password "password"
    Then they should see page title "My account - test_assessor - Complete a WebCAF self-assessment - GOV.UK"
    And text with "Logged in as:"
    And text with "Role:"
    And text with "Organisation:"
    And link with text "Change"
    And text with "You are reviewing Cyber Assessment Framework (CAF) self-assessments submitted by the"
    And they should see a table with header "System name and reference"
    And they should see a table with header "Sent for review date"
    And they should see a table with header "Review status"
    And they should see a table with header "Actions"


  Scenario: Assessor sees an enhanced submitted assessment on login
    Given there is a "enhanced" profile assessment  for "System 1", "Ministry of Agriculture", for the period "25/26" in "submitted" status and data "alice_completed_assessment.json"
    And the current assessment is assigned for review to the "Test Assessor company"
    And the user logs in with username  "test_assessor@example.com" and password "password"
    And Think time 1 seconds
    Then they should see page title "My account - test_assessor - Complete a WebCAF self-assessment - GOV.UK"
    And text with "System 1"
    And they should see a table with header "Sent for review date"
    And they should see a table with header "Review status"
    And they should see a table including value "System 1"
    And they should see a table including value "To do"
