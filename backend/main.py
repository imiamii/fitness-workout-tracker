from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from auth import create_access_token, hash_password, verify_password
from database import check_db, create_indexes, db
from deps import get_current_user
from models import Exercise, UserLogin, UserProfile, UserRegister, WorkoutCreate


app = FastAPI(title="Fitness & Workout Social App")


# --- CORS (frontend is plain HTML; allow localhost + file://)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Keep it simple for demo/debugging.
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.on_event("startup")
async def startup_db_client():
    await check_db()
    await create_indexes()


@app.get("/")
async def root():
    return {"message": "Fitness API is running"}


# ------------------------- AUTH -------------------------


@app.post("/auth/register", status_code=201)
async def register(user: UserRegister):
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_dict = user.dict()
    user_dict["password_hash"] = hash_password(user_dict.pop("password"))
    user_dict["profile"] = UserProfile().dict()

    result = await db.users.insert_one(user_dict)
    return {"id": str(result.inserted_id), "message": "User created successfully"}


@app.post("/auth/login")
async def login(user: UserLogin):
    db_user = await db.users.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(db_user["_id"])
    token = create_access_token({"sub": user_id})
    return {"access_token": token, "token_type": "bearer", "user_id": user_id}


# ------------------------- USERS -------------------------


@app.get("/me")
async def me(current_user=Depends(get_current_user)):
    return current_user


@app.patch("/users/{user_id}/profile")
async def update_profile(
    user_id: str,
    profile: UserProfile,
    current_user=Depends(get_current_user),
):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"profile": profile.dict(exclude_unset=True)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Profile updated"}


# ------------------------- WORKOUTS -------------------------


@app.post("/users/{user_id}/workouts", status_code=201)
async def create_workout(
    user_id: str,
    workout: WorkoutCreate,
    current_user=Depends(get_current_user),
):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    workout_dict = workout.dict()
    workout_dict["user_id"] = user_id  # reference to users collection
    workout_dict.setdefault("date", datetime.utcnow())
    workout_dict["exercises"] = []

    result = await db.workouts.insert_one(workout_dict)
    return {"id": str(result.inserted_id), "message": "Workout created"}


@app.get("/users/{user_id}/workouts")
async def get_user_workouts(
    user_id: str,
    current_user=Depends(get_current_user),
):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    cursor = db.workouts.find({"user_id": user_id}).sort("date", -1)
    workouts = await cursor.to_list(length=200)
    for w in workouts:
        w["id"] = str(w.pop("_id"))
    return workouts


@app.get("/workouts/{workout_id}")
async def get_workout(workout_id: str, current_user=Depends(get_current_user)):
    workout = await db.workouts.find_one({"_id": ObjectId(workout_id)})
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    if workout.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    workout["id"] = str(workout.pop("_id"))
    return workout


@app.patch("/workouts/{workout_id}/exercises")
async def add_exercise(
    workout_id: str,
    exercise: Exercise,
    current_user=Depends(get_current_user),
):
    # advanced update: $push (embedded documents)
    workout = await db.workouts.find_one({"_id": ObjectId(workout_id)})
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    if workout.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.workouts.update_one(
        {"_id": ObjectId(workout_id)},
        {"$push": {"exercises": exercise.dict()}},
    )
    return {"message": "Exercise added"}


@app.patch("/workouts/{workout_id}/exercises/remove")
async def remove_exercise(
    workout_id: str,
    exercise_name: str,
    current_user=Depends(get_current_user),
):
    # advanced update: $pull
    workout = await db.workouts.find_one({"_id": ObjectId(workout_id)})
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    if workout.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.workouts.update_one(
        {"_id": ObjectId(workout_id)},
        {"$pull": {"exercises": {"name": exercise_name}}},
    )
    return {"message": f"Removed {exercise_name}"}


@app.delete("/workouts/{workout_id}")
async def delete_workout(workout_id: str, current_user=Depends(get_current_user)):
    workout = await db.workouts.find_one({"_id": ObjectId(workout_id)})
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    if workout.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.workouts.delete_one({"_id": ObjectId(workout_id)})
    return {"message": "Workout deleted"}


# ------------------------- ANALYTICS (AGGREGATION) -------------------------


@app.get("/analytics/summary/{user_id}")
async def get_workout_stats(user_id: str, current_user=Depends(get_current_user)):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$unwind": {"path": "$exercises", "preserveNullAndEmptyArrays": True}},
        # First group by workout so total_workouts counts workouts (not exercises)
        {
            "$group": {
                "_id": "$_id",
                "user_id": {"$first": "$user_id"},
                "workout_volume": {
                    "$sum": {
                        "$multiply": [
                            {"$ifNull": ["$exercises.sets", 0]},
                            {"$ifNull": ["$exercises.reps", 0]},
                            {"$ifNull": ["$exercises.weight", 0]},
                        ]
                    }
                },
                "avg_reps_in_workout": {"$avg": "$exercises.reps"},
            }
        },
        # Then group by user for final summary
        {
            "$group": {
                "_id": "$user_id",
                "total_workouts": {"$sum": 1},
                "total_volume": {"$sum": "$workout_volume"},
                "avg_reps": {"$avg": "$avg_reps_in_workout"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "total_workouts": 1,
                "total_volume": {"$round": ["$total_volume", 1]},
                "avg_reps": {"$round": ["$avg_reps", 1]},
            }
        },
    ]

    cursor = db.workouts.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    return result[0] if result else {"total_workouts": 0, "total_volume": 0, "avg_reps": 0}
