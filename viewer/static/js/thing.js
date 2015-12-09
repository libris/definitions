$(function () {

  var expand = function (elem) {
    var $chip = elem.find('.chip-expanded');
    var $parent = elem;
    
    // Calculate if we're outside viewport
    var diff = ($parent.offset().left + $chip.width()) - $(window).width()
    var xMove = 1;
    if(diff > 0) {
      xMove += diff + 20;
    }
    $chip.css('margin-left', (-xMove));
    
    $chip.addClass('to-be-active');
    setTimeout(function() {
      if($chip.hasClass('to-be-active')) {
        $chip.addClass('active').removeClass('to-be-active');
        $chip.find('.panel-heading').focus();
        
        // Adjust Y-axis so that the panel will "grow" out of the chip
        if(!$chip.hasClass('adjustedTop')) {
          var $parentLabel = $parent.find('.panel-title').first();
          var yDiff = $parentLabel.offset().top - $chip.find('.panel-title').offset().top;
          if (yDiff !== 0) {
            $chip.css('margin-top', yDiff - 1);
            $chip.addClass('adjustedTop');
          }
        }
        
      }
    }, 500);
  };
  var collapse = function (elem) {
    var $chip = elem.find('.chip-expanded');
    $chip.removeClass('active').removeClass('to-be-active');
  }

  $('.link-item').each(function() {
    var $parent = $(this);
    $parent.append('<div class="chip-expanded">'+ $parent.html() +'</div>');
  });

  $('.link-item').hover(function() {
    expand($(this));
  }, function() {
    collapse($(this));
  }).focusin(function() {
    expand($(this));
  }).focusout(function() {
    collapse($(this));
  });

  $(document).ready(function () {
  });

});
