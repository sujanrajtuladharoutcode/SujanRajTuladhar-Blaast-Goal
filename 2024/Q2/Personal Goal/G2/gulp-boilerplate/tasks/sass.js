const { src, dest } = require('gulp')
const sass          = require('gulp-sass')(require('sass'))
const cssmin        = require('gulp-cssmin')
const postcss       = require('gulp-postcss')
const notify        = require('gulp-notify')
const cssnano       = require("cssnano")
const autoprefixer  = require('autoprefixer')

function sassBundle(cb) {
  return src('src/scss/**/**.scss', { sourcemaps: true })
    .pipe(sass())
    .on('error', notify.onError(function (error) {
        return "Sass: " + error.message;
    }))
    .pipe(postcss([autoprefixer(), cssnano()]))
    .pipe(dest('dist/css', { sourcemaps: '.' }));
  cb();
}

function cssMinify(cb) {
  return src('dist/css/style.css')
    .pipe(cssmin())
    .pipe(dest('dist/css'));
  cb();
}


exports.sassBundle = sassBundle;
exports.cssMinify = cssMinify;
