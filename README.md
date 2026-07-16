# Uncle's Wellness

I'm working on a website with a plain HTML/CSS frontend and a FastAPI backend. I need you to fix errors, connect the database to Firebase, push the code to GitHub, and deploy to Vercel. Go step by step and ask me before making any account-specific or credential-related decisions.

1. FIX ERRORS
   - Go through the FastAPI backend and identify errors: broken imports, missing dependencies in requirements.txt, incorrect route definitions, unhandled exceptions, CORS issues, etc.
   - Go through the HTML/CSS frontend and check for broken links, missing assets, console errors, and broken API calls to the backend (check the fetch/AJAX URLs match the FastAPI routes).
   - Run the backend locally (uvicorn) and confirm all endpoints respond correctly.
   - Open the frontend and confirm it loads and communicates with the backend without errors.
   - Fix any CORS configuration issues in FastAPI (add CORSMiddleware if missing) since frontend and backend will be deployed separately.

2. DATABASE — FIREBASE
   - Set up Firebase (ask me whether to use Firestore or Realtime Database if not already decided — I'd recommend Firestore for most cases).
   - Install and configure the Firebase Admin SDK in the FastAPI backend.
   - Use a service account key loaded via environment variables (never hardcoded) for authentication.
   - Migrate/connect any existing database logic (SQL, JSON files, etc.) to Firestore.
   - Confirm reads/writes work correctly by testing at least one endpoint end-to-end.

3. PUSH TO GITHUB
   - Initialize git if not already done, and make sure .env, service account keys, and other secrets are in .gitignore.
   - Create clear, logical commits describing the fixes and Firebase integration.
   - Push to my GitHub repository (ask me for the repo URL, or whether to create a new one).

4. DEPLOY TO VERCEL
   - Since Vercel is frontend/serverless-first, structure the project so:
     a) The HTML/CSS frontend deploys as a static site on Vercel.
     b) The FastAPI backend deploys as a Vercel serverless function (using a vercel.json config and an ASGI-compatible entry point, e.g. via mangum or Vercel's native Python runtime).
   - Set up all required environment variables in Vercel (Firebase credentials, API keys, etc.) — do not hardcode secrets.
   - Update frontend API calls to point to the deployed backend URL.
   - Confirm the production deployment builds and both frontend and backend work correctly live.
   - Share the final deployment URL(s).

Go through this step by step, show me what you're doing and why at each stage, and pause to ask if you hit a decision point (Firestore vs Realtime DB, repo name, missing credentials, etc.). Don't guess on anything involving credentials or account settings — ask me instead.
