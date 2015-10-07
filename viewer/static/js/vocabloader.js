$(function () {

  var loaded = false;
  var embedvocab = $('<div id="embedvocab"></div>').appendTo('body');

  $(document).on('click', 'body', function (event) {
    $('.state-active').removeClass('state-active');
  });

  $(document).on('click', '#embedvocab article.panel', function (event) {
    event.stopPropagation();
  });
  
    var termLinkSel = 'a[href^="/vocabview"]';
    var articleLinkSel = 'article.panel a[href^="#"]';
    var linkPos = {};
    
  function openTerm(ref, insidePopover) {
    
    
    function display() {
      
      $('.state-active').removeClass('state-active');
      $('#' + ref).addClass('state-active');
      
      if($('.main-item').length>0) {
        var flipOrientation = false;
        if(linkPos.right > $(window).width()/1.5) {
          flipOrientation = true;
        }
      }
      
      var popoverY = linkPos.Y - ($('.state-active').height()/2) + 8;
      $('.state-active .arrow').css('top', '50%');
      if (linkPos.Y < 300) {
        popoverY = linkPos.Y - ($('.state-active').height()/4) + 8;
        $('.state-active .arrow').css('top', '25%');
      }
      if (popoverY < 75)
        popoverY = 75;
      
      if(flipOrientation) {
        $('.state-active')
          .css('top', popoverY + "px")
          .css('left', (linkPos.X - $('.state-active').width() - 5) + "px")
          .addClass('left').removeClass('right');  
      }
      else {
        $('.state-active')
          .css('top', popoverY + "px")
          .css('left', (linkPos.right + 5) + "px")
          .addClass('right').removeClass('left');  
      }
          
      $('.state-active .panel-body').scrollTop(0);
        
      // if(insidePopover)
        $('.state-active .arrow').css('display', 'none');
      // else
        // $('.state-active .arrow').css('display', 'block');
        
    }
    if (!loaded) {
      embedvocab.append('<article class="panel text-center">' +
                        '<i class="glyphicon glyphicon-refresh btn-lg"></i></article>');
      embedvocab.load("/vocabview/ article.panel[id]", function() {
        $('article.panel[id]', this).
          addClass('popover').
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
    return false;
  });
    
  $(document).on('click', termLinkSel, function (e) {
    e.preventDefault();
    var ref = $(this).attr('href').replace(/[^#]*#(.*)/, "$1");
    
    linkPos.X = $(this).offset().left;
    linkPos.Y = $(this).offset().top;
    linkPos.right = $(this).offset().left + $(this).outerWidth();
    
    openTerm(ref, false);
    
    return false;
  });

});
