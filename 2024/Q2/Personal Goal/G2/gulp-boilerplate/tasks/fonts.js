const gulp = require('gulp');

function fonts() {
  return gulp.src('src/fonts/**/*')
    .pipe(gulp.dest('dist/fonts'));
}

exports.fonts = fonts
