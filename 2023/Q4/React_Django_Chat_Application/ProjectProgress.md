# Project Progress

## 1. Project Setup - Python, Django, and React

### Python and Django

- Installed Python and set up a virtual environment.
- Created a Django project using the command: `django-admin startproject projectname`.
- Created a Django app using the command: `python manage.py startapp appname`.
- Configured the database settings in `settings.py`.
- Applied migrations using the command: `python manage.py migrate`.
- Ran the Django development server using the command: `python manage.py runserver`.

### React

- Set up a new React project using Create React App: `npx create-react-app frontend`.
- Navigated into the React project directory: `cd frontend`.
- Started the React development server: `npm start`.

## 2. Setting Up Material-UI, Bootstrap, and Axios

- Installed Material-UI for React components.
- Configured Bootstrap for styling.
- Integrated Axios for making HTTP requests.
- Created `Register.js` and `App.js` components.
- Utilized TextField and Button components from Material-UI along with Bootstrap classes.

## 3. API Endpoint for User Registration

- Registered the `accounts` app and included `rest_framework` in `settings.py`.
- Gained understanding of HTTP status codes (201 and 400).
- Explored the `api_view` decorator in Django.
- Utilized the Postman extension in VS Code for testing.
- Made POST requests from Postman to test the user registration view and debugged errors.

## 4. Building a Secure Login API with Django REST and React

- Implemented a serializer for the login view, validating email and password.
- Established custom authentication using `TokenAuthentication`.
- Utilized static methods for token management (generation, extraction, verification, and authentication).
- Created a secure login view.
- Used read-only and write-only settings on the serializer.

## 5. Registering User with Django Rest Framework

- Employed `useState` for managing state in React components.
- Set up the base URL for API endpoints.
- Implemented the `HandleFormSubmit` function for form submission.
- Made the front-end user registration work using Axios and handled potential errors.
- Installed `django-cors-headers` on the backend for Cross-Origin Resource Sharing (CORS) support.

## Next Steps

- Continue with the remaining videos in the series.
- Explore Django Channels for real-time communication.
- Experiment with additional React features for a more dynamic user interface.
- Refine and expand the application's functionality based on project requirements.
