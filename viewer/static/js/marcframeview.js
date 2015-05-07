$(function () {

  var loaded = false;
  var embedvocab = $('<div id="embedvocab"></div>').appendTo('body');

  $(document).on('click', 'body', function (event) {
    $('.state-active').removeClass('state-active');
  });

  $(document).on('click', 'article.panel', function (event) {
    event.stopPropagation();
  });

  var termLinkSel = 'a[href^="../vocabview"], article.panel a[href^="#"]';
  $(document).on('click', termLinkSel, function () {
    var ref = $(this).attr('href').replace(/[^#]*#(.*)/, "$1");
    function display() {
      $('.state-active').removeClass('state-active');
      $('#' + ref).addClass('state-active');
    }
    if (!loaded) {
      embedvocab.append('<article class="panel state-active text-center">' +
                        '<i class="glyphicon glyphicon-refresh btn-lg"></i></article>');
      embedvocab.load("/vocabview/ article.panel[id]", function() {
        $('article.panel[id]', this).
          addClass('popover').
          addClass('right').
          prepend('<div class="arrow"></div>');
        $('a[href^="http"]').attr('target', '_blank').click(function (event) {
          event.stopPropagation();
        });
        display();
      });
      loaded = true;
    } else {
      display();
    }
    return false;
  });

});
