const gulp = require('gulp');
const gulpESLintNew = require('gulp-eslint-new');
const fs = require('fs'); // Import the fs module

// Define a task to create the 'dist' folder
function createDistFolder(cb) {
  try {
    fs.mkdirSync('dist', { recursive: true });
    // mkdir('dist', { recursive: true });
  } catch (error) {
    console.error('Error creating dist folder:', error);
  }
  cb();
}

function lint() {
  return gulp.src('./src/js/*.js')
    .pipe(gulpESLintNew())
    .pipe(gulpESLintNew.format())
    .pipe(gulpESLintNew.failAfterError());
}

function eslintFix() {
  return gulp.src('./src/js/index.js')
    .pipe(gulpESLintNew({ fix: true }))
    .pipe(gulpESLintNew.format())
    // If a file has a fix, overwrite it.
    .pipe(gulpESLintNew.fix())
}

exports.lint = lint
exports.eslintFix = eslintFix
exports.createDistFolder = createDistFolder; // Export the createDistFolder task
