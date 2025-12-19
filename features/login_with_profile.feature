Feature: User login with a profile


  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
#    Database does not store the passwords
    And the user "admin@example.gov.uk" exists
    And User "admin@example.gov.uk" has the profile "GovAssure lead" assigned in "Ministry of Agriculture"

  Scenario Outline: Valid user logs in <user_name>
    Given the application is running
    And cookies have been "accepted"
    And Think time 1 seconds
    When the user logs in with username  "<user_name>" and password "<password>"
    Then they should see page title "<page_title>"
    And page contains text "<page_text>" in banner
    Examples:
      | user_name            | password | page_title                                                      | page_text                                                                                                                                        |
      | admin@example.gov.uk | password | GovAssure lead - My account - admin - Complete a WebCAF self-assessment - GOV.UK | You cannot start a new self-assessment, until your scoping document is signed off and your system has been added to WebCAF by a cyber adviser. |
