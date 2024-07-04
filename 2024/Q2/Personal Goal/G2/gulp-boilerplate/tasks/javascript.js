const { src, dest } = require('gulp')
const browserify    = require('browserify')
const babelify      = require('babelify')
const source        = require('vinyl-source-stream')
const notify        = require("gulp-notify")
const uglify        = require('gulp-uglify')
const stripDebug    = require('gulp-strip-debug')
const concat = require('gulp-concat');
const rename = require('gulp-rename');

function jsBundle(cb) {
  return browserify('src/js/index.js')
    .transform(babelify, {
      presets: ['@babel/preset-env'],
      plugins: ['@babel/plugin-transform-runtime', '@babel/plugin-proposal-object-rest-spread'],
      sourceMapsAbsolute: true
    })
    .bundle()
    .on('error', notify.onError(function (error) {
        return "JS: " + error.message;
    }))
    .pipe(source('index.js'))
    .pipe(dest('dist/js'));
  cb();
}

function jsConcat(cb) {
  return src(['./src/js/plugins/*.js', './src/js/index.js'])
    .pipe(concat('index.js', { newLine: '\r\n'}))
    .pipe(rename({ suffix: '.min' }))
    .pipe(dest('./dist/js/'));
  cb()
}

function jsMinify(cb) {
  return src('dist/js/index.js')
    .pipe(uglify())
    .pipe(stripDebug())
    .pipe(dest('dist/js'));
  cb();
}

exports.jsBundle = jsBundle;
exports.jsMinify = jsMinify;
exports.jsConcat = jsConcat;
