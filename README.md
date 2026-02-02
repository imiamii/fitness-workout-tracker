# Fitness & Workout Social App (MongoDB + FastAPI)

## Project overview
Small fitness tracker web app where users can register/login, create workouts, add exercises, and view progress analytics.

## Tech: MongoDB (NoSQL), FastAPI (Python), plain HTML/CSS/JS frontend.



## System architecture
**Frontend (HTML/JS)** → HTTP (fetch) → **FastAPI REST API** → **MongoDB** (Motor async driver).

Authentication: JWT (stored in browser localStorage, sent as `Authorization: Bearer <token>`).



## Database schema

### `users` collection (embedded model)
One document per user. Contains an **embedded** `profile` object.

Example shape:
```js
{
  _id: ObjectId(...),
  username: "john_doe",
  email: "john@test.com", // unique
  password_hash: "...",
  profile: {
    age: 20,
    weight: 75,
    height: 180,
    goals: "Stay fit"
  }
}
```

### `workouts` collection (referenced + embedded)
Workouts are stored separately and **reference** a user via `user_id`. Exercises are **embedded** inside a workout document.

Example shape:
```js
{
  _id: ObjectId(...),
  user_id: "<user _id as string>",
  title: "Upper Body",
  date: ISODate(...),
  exercises: [
    { name: "Bench press", sets: 3, reps: 10, weight: 40 }
  ]
}
```

Why this modeling:
- `user.profile` is embedded because it is always read with the user.
- `workouts.user_id` is a reference because workouts can grow and are fetched separately.
- `workouts.exercises` is embedded because exercises are not queried independently from the workout.

---

## Indexing & optimization
Indexes are created on backend startup:

1) **Unique index** on `users.email` (prevents duplicate accounts)
2) **Compound index** on `workouts (user_id, date)` for the main query pattern: “get my workouts sorted by newest”




### Authentication
- `POST /auth/register` (create user)
- `POST /auth/login` (returns JWT + user_id)

### Users
- `GET /me` (auth required)
- `PATCH /users/{user_id}/profile` (advanced update: `$set` on embedded profile)

### Workouts (CRUD)
- `POST /users/{user_id}/workouts` (create workout)
- `GET /users/{user_id}/workouts` (read workouts list)
- `GET /workouts/{workout_id}` (read single workout)
- `DELETE /workouts/{workout_id}` (delete workout)

### Advanced updates
- `PATCH /workouts/{workout_id}/exercises` (advanced update: `$push` embedded exercise)
- `PATCH /workouts/{workout_id}/exercises/remove?exercise_name=Bench%20press` (advanced update: `$pull`)

### Aggregation endpoint
- `GET /analytics/summary/{user_id}` (multi-stage aggregation: total workouts, total volume, avg reps)



## MongoDB queries used (examples)

### Read workouts (uses compound index)
```js
db.workouts.find({ user_id: "<id>" }).sort({ date: -1 })
```

### Advanced updates
```js
// $push exercise
db.workouts.updateOne(
  { _id: ObjectId("...") },
  { $push: { exercises: { name: "Bench", sets: 3, reps: 10, weight: 40 } } }
)

// $pull exercise by name
db.workouts.updateOne(
  { _id: ObjectId("...") },
  { $pull: { exercises: { name: "Bench" } } }
)
```

### Aggregation
```js
db.workouts.aggregate([
  { $match: { user_id: "<id>" } },
  { $unwind: { path: "$exercises", preserveNullAndEmptyArrays: true } },
  { $group: {
      _id: "$_id",
      user_id: { $first: "$user_id" },
      workout_volume: { $sum: { $multiply: ["$exercises.sets", "$exercises.reps", "$exercises.weight"] } },
      avg_reps_in_workout: { $avg: "$exercises.reps" }
  } },
  { $group: {
      _id: "$user_id",
      total_workouts: { $sum: 1 },
      total_volume: { $sum: "$workout_volume" },
      avg_reps: { $avg: "$avg_reps_in_workout" }
  } },
  { $project: { _id: 0, total_workouts: 1, total_volume: 1, avg_reps: 1 } }
])
```

---

## How to run

### 1) Start MongoDB locally
Make sure MongoDB is running on `mongodb://localhost:27017`.

### 2) Run backend
```bash
cd fitness_app/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3) Run frontend
Open `fitness_app/frontend/index.html` with **VS Code Live Server** (recommended), then:
- Register
- Login
- Create a workout and add exercises
- View dashboard stats + history



## Pages (frontend)
Minimum required: **4 pages**
- `index.html` (landing)
- `auth.html` (login/register)
- `dashboard.html` (history + delete + analytics summary)
- `workout_creator.html` (create workout + add exercises)
