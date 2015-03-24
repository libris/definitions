$(function () {

  var loaded = false;
  var embedvocab = $('<div id="embedvocab"></div>').appendTo('body');

  $(document).on('click', 'body', function (event) {
    $('.active').removeClass('active');
  });

  $(document).on('click', 'article.panel', function (event) {
    event.stopPropagation();
  });

  var termLinkSel = 'a[href^="../vocabview"], article.panel a[href^="#"]';
  $(document).on('click', termLinkSel, function () {
    var ref = $(this).attr('href').replace(/[^#]*#(.*)/, "$1");
    function display() {
      $('.active').removeClass('active');
      $('#' + ref).addClass('active');
    }
    if (!loaded) {
      embedvocab.append('<article class="panel active text-center">' +
                        '<i class="glyphicon glyphicon-refresh btn-lg"></i></article>');
      embedvocab.load("/vocabview/ article.panel[id]", function() {
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
