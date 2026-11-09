Feature: User login without a profile

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
#    Database does not store the passwords
    And the user "alice@example.gov.uk" exists
  Scenario Outline: Valid user logs in <user_name>
    Given the application is running
    And cookies have been "accepted"
    And Think time 1 seconds
    When the user signs in with One Login as "<user_name>"
    Then they should see page title "<page_title>"
    And page contains text "<page_text>" in banner
    Examples:
      | user_name            | page_title                                                      | page_text                                                                              |
      | alice@example.gov.uk | My account - alice - Complete a WebCAF self-assessment - GOV.UK | You do not have a profile set up. Please create one by contacting your GovAssure lead. |

  Scenario Outline: New valid user logs in <user_name>
    Given the application is running
    And cookies have been "accepted"
    And Think time 1 seconds
    When the user signs in with One Login as "<user_name>"
    Then they should see page title "<page_title>"
    And page contains text "<page_text>" in header

    Examples:
      | user_name             | page_title                                                                     | page_text                         |
      | alice1@example.gov.uk | Your email domain is not approved - Complete a WebCAF self-assessment - GOV.UK | Your email domain is not approved |