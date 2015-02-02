$(function () {

  var loaded = false;
  vocabview = $('iframe[name=vocabview]');
  vocabview.hide();

  vocabview.load(function () {
    var contents = $(this).contents();
    $('body', contents).addClass('compact');
  });

  $('body').on('click', function () {
    vocabview.hide();
  });

  $('a[href^="../vocabview"]').click(function (event) {
    if (!loaded) {
      vocabview.attr('src', "/vocabview/");
      loaded = true;
    }
    vocabview.show();
    event.stopPropagation();
  });

});
