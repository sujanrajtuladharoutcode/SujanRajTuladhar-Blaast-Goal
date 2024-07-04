const gulp = require('gulp');
const gulpStylelint = require('gulp-stylelint');

function stylelintfix() {
  return gulp.src('./src/scss/components/*.scss')
    .pipe(gulpStylelint({
      fix: true,
      reporters: [
        {formatter: 'string', console: true}
      ]
    }))
    .pipe(gulp.dest('src/scss/components'));
}

exports.stylelintfix = stylelintfix






