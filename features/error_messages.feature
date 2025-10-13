Feature: Test user error messages appear as expected

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
    And the user "other@example.gov.uk" exists
    And User "other@example.gov.uk" has the profile "Organisation lead" assigned in "Ministry of Agriculture"
    And the application is running
    And the user logs in with username  "other@example.gov.uk" and password "password"

Scenario: New assessment no profile is selected
    Given Think time 1 seconds
    And click button with text "Start a self-assessment"
    And click link with text "Choose your government CAF profile"
    And click button with text "Save and continue"
    # Then should see an error summary with error link text "CAF profile : This field is required."
    Then should see an error message with text "You must select a profile."

Scenario: New assessment no review type is selected
    Given Think time 1 seconds
    And click button with text "Start a self-assessment"
    And click link with text "Choose a review type"
    And click button with text "Save and continue"
    Then should see an error summary with error link text "Review type : This field is required."
    Then should see an error message with text "You must select a review type."

Scenario: Manage User yes or no not selected
    Given Think time 1 seconds
    And click link with text "Manage users"
    And click button with text "Continue"
    Then should see an error summary with error link text "Add another user : This field is required."
    Then should see an error message with text "You must select yes or no"

Scenario: Create new user but omit last name
    Given Think time 1 seconds
    And click link with text "Manage users"
    And select radio with value "yes"
    And click button with text "Continue"
    And enter text "The" for id "first_name"
    And enter text "the.tester@example.gov.uk" for id "email"
    And select radio with value "organisation_user"
    And click button with text "Save and continue"
    Then should see an error summary with error link text "Last name : This field is required."
    Then should see an error message with text "You must add a last name"

Scenario: Nothing selected on indicators page
    Given Think time 1 seconds
    And click button with text "Start a self-assessment"
    And click link with text "Provide system details"
    And select select box with value "System 2"
    And click button with text "Save and continue"
    And click link with text "Choose your government CAF profile"
    And select radio with value "baseline"
    And click button with text "Save and continue"
    And click link with text "Choose a review type"
    And select radio with value "peer_review"
    And click button with text "Save and continue"
    And get assessment id from url and add to context
    Then navigate to "Objective A: Managing security risk"
    And Fill outcome "A1.a Board Direction" with "achieved, partially-achieved, not-achieved" with "none,none,none"
    Then should see an error summary with error link text "You need to select at least one statement to answer"

Scenario: Nothing selected indicator confirmation page
    Given Think time 1 seconds
    And click button with text "Start a self-assessment"
    And click link with text "Provide system details"
    And select select box with value "System 2"
    And click button with text "Save and continue"
    And click link with text "Choose your government CAF profile"
    And select radio with value "baseline"
    And click button with text "Save and continue"
    And click link with text "Choose a review type"
    And select radio with value "peer_review"
    And click button with text "Save and continue"
    And get assessment id from url and add to context
    Then navigate to "Objective A: Managing security risk"
    And Fill outcome "A1.a Board Direction" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And click button with text "Save and continue"
    Then should see an error summary with error link text "Confirm outcome : This field is required."
    Then should see an error message with text "You must confirm you agree with the status or change your response."
