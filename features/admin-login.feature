Feature: Admin user login

  Background:
    Given the user "admin2" with the "admin" exists in the backend
    And no login attempt blocks for the user "admin2"

  Scenario: Can login with correct password
    Given the user is on the admin login page
    And Think time 1 seconds
    And enter text "admin2" for id "id_username"
    And enter text "admin" for id "id_password"
    And click button with text "Log in"
    Then they should see page title "Site administration | Django site admin"

  Scenario: Five incorrect attempts locks the user
    Given the user is on the admin login page
    And enter text "admin2" for id "id_username"
    And enter text "admin1" for id "id_password"
    And click button with text "Log in"
    And enter text "admin2" for id "id_username"
    And enter text "admin2" for id "id_password"
    And click button with text "Log in"
    And enter text "admin2" for id "id_username"
    And enter text "admin3" for id "id_password"
    And click button with text "Log in"
    And enter text "admin2" for id "id_username"
    And enter text "admin4" for id "id_password"
    And click button with text "Log in"
    And enter text "admin2" for id "id_username"
    And enter text "admin5" for id "id_password"
    And click button with text "Log in"
    Then they should see page title "Forbidden"
    And page has heading "Too many login attempts"
