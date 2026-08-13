# bugs and failures
- [x] the data that contains muscles and stuff isnt being added to database
  (was: Exercise model had no `muscles` relationship, no migration created the
  `exercise_muscle` table, and seed_data crashed with `TypeError`)
- [x] there shouldnt be a need to specify which muscle a given exercise trains when adding an exercise to a session
  (muscles are now a property of the exercise; sessions only reference `exercise_id`)

# To learn
- [x] Make sure I understand how fixtures work
- [x] Understand the conftest file
- [x] Do tables get erased after each test?
  (conftest: tables are created once per session; each test runs in a transaction
  that is rolled back afterwards, so tests are isolated)

# To implement
- [x] user authentication (register + login + JWT bearer)
- [x] exercises into database (API + seed data + migration)
- [x] user adding their exercises (POST /exercises)
- [x] a workoutset must be modifiable (PATCH /sessions/{id}/workout-sets/{set_id})
- [x] user must be able to delete their workouts or any given set
  (DELETE /sessions/{id} and DELETE /sessions/{id}/workout-sets/{set_id})

# To do
- [x] Start with documentation (README)
- [ ] Create a new test for passwords
- [ ] Check passwords an auth code
- [ ] Create a front end for the app
