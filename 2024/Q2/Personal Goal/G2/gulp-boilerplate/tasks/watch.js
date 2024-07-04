const { watch, series } = require('gulp')
const { sassBundle }      = require('./sass')
const { jsBundle, jsConcat }        = require('./javascript')
const { browsersyncReload } = require('./livereload')
const { html } = require("./html");
//const { eslintFix } = require("./eslint");
//const { stylelintfix } = require("./stylelint");
const { img } = require("./img");
const { video } = require("./video");

function watcher() {
  watch("src/**/**.html", series(html, browsersyncReload));
  watch(
    ['src/scss/**/**/*.scss'],
    {queue: false},
    //series(stylelintfix ,sassBundle, browsersyncReload));
    series(sassBundle, browsersyncReload));
  watch(
    ['src/js/**/*.js'],
    //series(eslintFix, jsBundle, jsConcat, browsersyncReload));
    series(jsBundle, jsConcat, browsersyncReload));
  watch(
    ['src/img/**/*'],
    series(img, browsersyncReload));
  watch(
    ['src/video/**/*'],
    series(video, browsersyncReload));
}

exports.watcher = watcher;
