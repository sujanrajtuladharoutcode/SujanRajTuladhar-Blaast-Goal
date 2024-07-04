const gulp = require('gulp');
const sass = require('gulp-sass');
const eslint = require('gulp-eslint');
const browserSync = require('browser-sync').create();
// const fs = require('fs'); // Require the 'fs' module to work with the file system
const cleanCSS = require('gulp-clean-css');

// Define a task to create the 'dist' folder
// function createDistFolder(cb) {
//     try {
//       // Check if the 'dist' directory exists, if not, create it
//       if (!fs.existsSync('dist')) {
//         fs.mkdirSync('dist', { recursive: true });
//       }
//       console.log('Dist folder created successfully.');
//     } catch (error) {
//       console.error('Error creating dist folder:', error);
//     }
//     cb();
// }

const fs = require('fs');

function createDistFolder(cb) {
  // Delete the 'dist' directory if it exists
  if (fs.existsSync('dist')) {
    deleteFolderRecursive('dist');
    console.log('Deleted existing dist folder.');
  }

  // Create the 'dist' directory
  try {
    fs.mkdirSync('dist', { recursive: true });
    console.log('Dist folder created successfully.');
  } catch (error) {
    console.error('Error creating dist folder:', error);
  }

  cb();
}

// Recursive function to delete a directory and its contents
function deleteFolderRecursive(path) {
  if (fs.existsSync(path)) {
    fs.readdirSync(path).forEach(file => {
      const curPath = `${path}/${file}`;
      if (fs.lstatSync(curPath).isDirectory()) {
        // Recursive call for directories
        deleteFolderRecursive(curPath);
      } else {
        // Delete files
        fs.unlinkSync(curPath);
      }
    });
    // Delete the directory itself
    fs.rmdirSync(path);
  }
}


// Define paths
const paths = {
  src: {
    // scss: 'src/scss/**/*.scss',
    css: 'src/css/**/*.css',
    js: 'src/js/**/*.js',
    html: 'src/**/*.html',
    fonts: 'src/fonts/**/*',
    images: 'src/images/**/*'
  },
  dest: {
    css: 'dist/css',
    js: 'dist/js',
    html: 'dist',
    fonts: 'dist/fonts',
    images: 'dist/images'
  }
};

// Sass task: compile SCSS files into CSS
// function sassTask() {
//   return gulp.src(paths.src.scss)
//     .pipe(sass())
//     .pipe(gulp.dest(paths.dest.css))
//     .pipe(browserSync.stream());
// }

// Sass task: compile SCSS files into CSS
function cssTask() {
    return gulp.src(paths.src.css)
      .pipe(cleanCSS()) // Minify the CSS files
      .pipe(gulp.dest(paths.dest.css))
      .pipe(browserSync.stream());
  }

// JavaScript task: lint and concatenate JS files
function jsTask() {
    // Check if the 'dist' directory exists, if not, create it
//   if (!fs.existsSync(paths.dest.js)) {
//     fs.mkdirSync(paths.dest.js, { recursive: true });
//   }

  return gulp.src(paths.src.js)
    .pipe(eslint())
    .pipe(eslint.format())
    .pipe(gulp.dest(paths.dest.js))
    .pipe(browserSync.stream());
    // .pipe(gulp.dest(paths.dest.js))
}

// HTML task: move HTML files to the dist folder
function htmlTask() {
  return gulp.src(paths.src.html)
    .pipe(gulp.dest(paths.dest.html))
    .pipe(browserSync.stream());
}

// Fonts task: move font files to the dist folder
function fontsTask() {
  return gulp.src(paths.src.fonts)
    .pipe(gulp.dest(paths.dest.fonts));
}

// Images task: move image files to the dist folder
function imagesTask() {
  return gulp.src(paths.src.images)
    .pipe(gulp.dest(paths.dest.images));
}

// Watch task: watch for file changes and reload browser
function watchTask() {
  browserSync.init({
    server: {
      baseDir: './dist'
    }
  });

//   gulp.watch(paths.src.scss, sassTask);
  gulp.watch(paths.src.css, cssTask);
  gulp.watch(paths.src.js, jsTask);
  gulp.watch(paths.src.html, htmlTask);
  gulp.watch(paths.src.html, fontsTask);
  gulp.watch(paths.src.html, imagesTask);
}

// Define tasks
exports.default = gulp.series(
//   gulp.parallel(sassTask, jsTask, htmlTask, fontsTask, imagesTask),
  gulp.parallel(createDistFolder, cssTask, jsTask, htmlTask, fontsTask, imagesTask),
  watchTask
);
