import mongoose, { Connection } from "mongoose";


let cachedConnection: Connection | null = null;


export async function connectToMongoDB() {
  
  if (cachedConnection) {
    console.log("Using cached db connection");
    return cachedConnection;
  }
  try {
    // Mongoose's default serverSelectionTimeoutMS is 30s — every signup/signin
    // call would block that long before userStore.ts's local-file fallback
    // kicked in whenever MONGODB_URI is set but nothing is listening on it
    // (the common case for a local/demo run). 3s is enough for a real,
    // reachable Mongo instance and fails fast otherwise.
    const cnx = await mongoose.connect(process.env.MONGODB_URI!, {
      serverSelectionTimeoutMS: 3000,
    });

    cachedConnection = cnx.connection;

    console.log("New mongodb connection established");

    return cachedConnection;
  } catch (error) {
    console.log(error);
    throw error;
  }
}