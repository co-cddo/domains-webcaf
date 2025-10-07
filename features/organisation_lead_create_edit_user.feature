Feature: Create and edit a new user for the organisation

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
#    Database does not store the passwords
    And the user "other@example.gov.uk" exists
    And User "other@example.gov.uk" has the profile "Organisation lead" assigned in "Ministry of Agriculture"
    And the application is running
    And the user logs in with username  "other@example.gov.uk" and password "password"

  Scenario: Organisation lead can see option to create users and create an Organisation user and then edit
    Given Think time 2 seconds
    Then they should see page title "My account - other - Complete a WebCAF self-assessment - GOV.UK"
    And check user is logged in against organisation "Ministry of Agriculture"
    And a button with text "Start a self-assessment"
    And link with text "Your organisation details"
    And link with text "Manage users"
    When click link with text "Manage users"
    Then they should see page title "Manage users - other - Complete a WebCAF self-assessment - GOV.UK"
    And select radio with value "confirm"
    And click button with text "Continue"
    Then they should see page title "Manage user - other - Complete a WebCAF self-assessment - GOV.UK"
    And enter text "The" for id "first_name"
    And enter text "Tester" for id "last_name"
    And enter text "the.tester@example.gov.uk" for id "email"
    And select radio with value "organisation_user"
    And click button with text "Save and continue"
    Then they should see page title "Manage user - other - Complete a WebCAF self-assessment - GOV.UK"
    Then they should see a summary card with header "Ministry of Agriculture" keys "Full name, Email address, User role" and values "The Tester, the.tester@example.gov.uk, organisation_user"
    And a button with text "Change"
    And click button with text "Save and continue"
    Then User model with email "the.tester@example.gov.uk" should exist with "organisation_user" user role

  Scenario: Organisation lead can edit user profile role
    Given the user "alice@example.gov.uk" exists
    And User "alice@example.gov.uk" has the profile "Organisation user" assigned in "Ministry of Agriculture"
    Given Think time 2 seconds
    Then they should see page title "My account - other - Complete a WebCAF self-assessment - GOV.UK"
    And a button with text "Start a self-assessment"
    And link with text "Your organisation details"
    And link with text "Manage users"
    When click link with text "Manage users"
    Then they should see page title "Manage users - other - Complete a WebCAF self-assessment - GOV.UK"
    Then they should see a table including value "alice@example.gov.uk"
    And link with text "Change"
    And link with text "Remove"
    When click link in table row containing value "alice@example.gov.uk" with text "Change"
    Then they should see page title "Manage user - other - Complete a WebCAF self-assessment - GOV.UK"
    And enter text "Tester" for id "last_name"
    And select radio with value "organisation_lead"
    And click button with text "Save and continue"
    Then they should see page title "Manage user - other - Complete a WebCAF self-assessment - GOV.UK"
    Then they should see a summary card with header "Ministry of Agriculture" keys "Full name, Email address, User role" and values "alice Tester, alice@example.gov.uk, organisation_lead"
    And a button with text "Change"
    And click button with text "Save and continue"
    Then User model with email "alice@example.gov.uk" should exist with "organisation_lead" user role
