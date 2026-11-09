@one_login
Feature: GOV.UK One Login authentication

  Scenario: Existing user with a profile signs in
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1"
    And the user "admin@example.gov.uk" exists
    And User "admin@example.gov.uk" has the profile "GovAssure lead" assigned in "Ministry of Agriculture"
    And the application is running
    And cookies have been "accepted"
    When the user signs in with One Login as "admin@example.gov.uk"
    Then page contains text "My GovAssure lead account" in header

  Scenario: Existing user without a profile signs in
    Given the user "alice@example.gov.uk" exists
    And the application is running
    And cookies have been "accepted"
    When the user signs in with One Login as "alice@example.gov.uk"
    Then page contains text "You do not have a profile set up" in banner

  Scenario: User with an unverified email is rejected
    Given the user "alice@example.gov.uk" exists
    And the application is running
    And cookies have been "accepted"
    When the user attempts to sign in with an unverified One Login email "alice@example.gov.uk"
    Then page contains text "There is a problem signing you in" in header

  Scenario: Existing user logs out through One Login
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1"
    And the user "admin@example.gov.uk" exists
    And User "admin@example.gov.uk" has the profile "GovAssure lead" assigned in "Ministry of Agriculture"
    And the application is running
    And cookies have been "accepted"
    And the user signs in with One Login as "admin@example.gov.uk"
    When the user logs out through One Login
    Then they should see page title "Start page  - Complete a WebCAF self-assessment - GOV.UK"

Scenario: User without an approved domain signs in
    Given the application is running
    And cookies have been "accepted"
    When the user signs in with One Login as "abc@nodomain.com"
    Then page contains text "Your email domain is not approved" in header