# Auth testing
1. mongosh test_database: db.users.find({role:"admin"}) → bcrypt hash starts with $2b$; unique index users.email.
2. curl -c c.txt -X POST $URL/api/auth/login -H 'Content-Type: application/json' -d '{"email":"seunolawepo2010@gmail.com","password":"<see test_credentials.md>"}'
3. curl -b c.txt $URL/api/auth/me → admin user. Admin endpoints /api/admin/* must return 401 without cookie.
4. 5 failed logins from same IP+email → 429 lockout for 15 minutes.
