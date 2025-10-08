  Feature: Remove a user for the organisation

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
#    Database does not store the passwords
    And the user "other@example.gov.uk" exists
    And User "other@example.gov.uk" has the profile "Organisation lead" assigned in "Ministry of Agriculture"
    And the user "alice@example.gov.uk" exists
    And User "alice@example.gov.uk" has the profile "Organisation user" assigned in "Ministry of Agriculture"
    And the application is running
    And the user logs in with username  "other@example.gov.uk" and password "password"

    Scenario: Organisation lead can remove user
        Given Think time 1 seconds
        Then they should see page title "My account - other - Complete a WebCAF self-assessment - GOV.UK"
        And check user is logged in against organisation "Ministry of Agriculture"
        When click link with text "Manage users"
        Then they should see page title "Manage users - other - Complete a WebCAF self-assessment - GOV.UK"
        Then they should see a table including value "alice@example.gov.uk"
        And link with text "Change"
        And link with text "Remove"
        When click link in table row containing value "alice@example.gov.uk" with text "Remove"
        And select radio with value "confirm"
        And click button with text "Continue"
        Then they should see a table without value "alice@example.gov.uk" in any row
        And click button with text "Continue"
        Then User profile model with email "alice@example.gov.uk" should not exist
