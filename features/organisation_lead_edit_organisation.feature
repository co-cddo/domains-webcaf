Feature: Organisation lead can edit an organisation's details

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
#    Database does not store the passwords
    And the user "other@example.gov.uk" exists
    And User "other@example.gov.uk" has the profile "Organisation lead" assigned in "Ministry of Agriculture"
    And the application is running
    And the user logs in with username  "other@example.gov.uk" and password "password"


    Scenario: Organisation lead can edit organisation
        Given Think time 2 seconds
        Then they should see page title "My account - other - Complete a WebCAF self-assessment - GOV.UK"
        And check user is logged in against organisation "Ministry of Agriculture"
        And a button with text "Start a self-assessment"
        And link with text "Your organisation details"
        And link with text "Manage users"
        When click link with text "Your organisation details"
        Then they should see a summary card with header "About the organisation" keys "Name, Type, Parent organisation" and values "Ministry of Agriculture, -, -"
        Then they should see a summary card with header "Additional contact information" keys "Name, Role, Email address" and values "None, None, None"
        And click link in summary card row "Type" with text "Change"
        And select radio with value "public-corporation"
        And click button with text "Continue"
        And enter text "Tess Tester" for id "contact_name"
        And enter text "Tester" for id "contact_role"
        And enter text "tess.tester@example.gov.uk" for id "contact_email"
        And click button with text "Continue"
        Then they should see a summary card with header "About the organisation" keys "Name, Type, Parent organisation" and values "Ministry of Agriculture, Public corporation, -"
        Then they should see a summary card with header "Additional contact information" keys "Name, Role, Email address" and values "Tess Tester, Tester, tess.tester@example.gov.uk"
        Then check organisation "Ministry of Agriculture" has type "public-corporation" and contact details "Tess Tester" "Tester" and "tess.tester@example.gov.uk"
