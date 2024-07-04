const gulp = require('gulp');

function video() {
  return gulp.src('src/video/**/*')
    .pipe(gulp.dest('dist/video'));
}

exports.video = video
