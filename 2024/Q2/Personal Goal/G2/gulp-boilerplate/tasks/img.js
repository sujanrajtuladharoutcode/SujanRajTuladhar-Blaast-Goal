const gulp = require('gulp');

function img() {
  return gulp.src('src/img/**/*')
    .pipe(gulp.dest('dist/img'));
}

exports.img = img
