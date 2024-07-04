const gulp = require('gulp');
const gulpIf = require('gulp-if');
const htmlmin = require('gulp-htmlmin');
const htmlPartial = require('gulp-html-partial');
const isProd = process.env.NODE_ENV === 'production';

const htmlFile = [
  'src/**/**.html'
]

function html() {
  return gulp.src(htmlFile)
    .pipe(htmlPartial({
      basePath: 'src/partials/'
    }))
    .pipe(gulpIf(isProd, htmlmin({
      collapseWhitespace: true
    })))
    .pipe(gulp.dest('dist'));
}

exports.html = html
