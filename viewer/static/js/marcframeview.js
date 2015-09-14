$(function () {

  var loaded = false;
  var embedvocab = $('<div id="embedvocab"></div>').appendTo('body');

  $(document).on('click', 'body', function (event) {
    $('.state-active').removeClass('state-active');
  });

  $(document).on('click', 'article.panel', function (event) {
    event.stopPropagation();
  });
  
    var termLinkSel = 'a[href^="../vocabview"]';
    var articleLinkSel = 'article.panel a[href^="#"]';
    var linkPos = {};
    
  function openTerm(ref, insidePopover) {
    
    function display() {
      $('.state-active').removeClass('state-active');
      $('#' + ref).addClass('state-active');
      
      $('.state-active')
        .css('top', linkPos.Y - ($('.state-active').height()/2) + 8 + "px")
        .css('left', (linkPos.X + 10) + "px");
      $('.state-active .panel-body').scrollTop(0);
        
      if(insidePopover)
        $('.state-active .arrow').css('display', 'none');
      else
        $('.state-active .arrow').css('display', 'block');
        
    }
    if (!loaded) {
      embedvocab.append('<article class="panel text-center">' +
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
    
  }
    
  $(document).on('click', articleLinkSel, function (e) {
    e.preventDefault();
    var ref = $(this).attr('href').replace(/[^#]*#(.*)/, "$1");
    
    openTerm(ref, true);
  });
    
  $(document).on('click', termLinkSel, function (e) {
    var ref = $(this).attr('href').replace(/[^#]*#(.*)/, "$1");
    
    linkPos.X = $(this).offset().left + $(this).outerWidth();
    linkPos.Y = $(this).offset().top;
    
    openTerm(ref, false);
    
    return false;
  });

});
