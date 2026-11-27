Feature: Organisation lead can view an organisation's details

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
#    Database does not store the passwords
    And the user "other@example.gov.uk" exists
    And User "other@example.gov.uk" has the profile "GovAssure lead" assigned in "Ministry of Agriculture"
    And the application is running
    And cookies have been "accepted"
    And the user signs in with One Login as "other@example.gov.uk"


    Scenario: GovAssure lead can view organisation
        Given Think time 1 seconds
        Then they should see page title "GovAssure lead - My account - other - Complete a WebCAF self-assessment - GOV.UK"
        And check user is logged in against organisation "Ministry of Agriculture"
        And a button with text "Start a self-assessment"
        And link with text "Your organisation details"
        And link with text "Manage users"
        When click link with text "Your organisation details"
        Then they should see a summary card with header "About the organisation" keys "Name, Type" and values "Ministry of Agriculture, -"
