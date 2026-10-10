# Frontend deployment

This directory is the Flutter application. In Vercel, set the project Root
Directory to `frontend` and publish the generated `build/web` directory.

Build the web app with the deployed API URL compiled in:

```sh
flutter build web --release \
  --dart-define=API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com \
  --dart-define=SUPABASE_URL=https://YOUR-PROJECT.supabase.co \
  --dart-define=SUPABASE_PUBLISHABLE_KEY=YOUR-PUBLISHABLE-KEY
```

The build environment must have the Flutter SDK installed. Do not add database
passwords, Supabase service-role keys, or other backend secrets to Vercel's
frontend environment; browser builds are public.
