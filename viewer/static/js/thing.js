$(function () {

  $('.link-item').each(function() {
    $(this).append('<div class="chip-expanded">'+ $(this).html() +'</div>');
    var chip = $(this).find('.chip-expanded');
    // chip.css('display', 'none');
    var y = $(this).offset().top - parseInt($(document.body).css('padding-top')) - 32;
    chip.css('top', y);
    var x = $(this).offset().left;
    if (x + chip.width() > $(document.body).width()) {
      console.log("x + chipwidth", x + chip.width())
      console.log("doc width", $(document.body).width());
      var xDiff = x + chip.width() - $(document.body).width();
      chip.css('margin-left', -(xDiff+20));
    }
  });
  
  $('.link-item').hover(function() {
    var chip = $(this).find('.chip-expanded');
    // chip.addClass('to-be-active').removeClass('to-be-inactive');
    chip.addClass('to-be-active');
    setTimeout(function() {
      if(chip.hasClass('to-be-active'))
        chip.addClass('active').removeClass('to-be-active');
        // chip.addClass('active').css('display', 'block').removeClass('to-be-active');
    }, 750);
  }, function() {
    var chip = $(this).find('.chip-expanded');
    chip.removeClass('active').removeClass('to-be-active');
    // chip.removeClass('active').removeClass('to-be-active').addClass('to-be-inactive');
    // setTimeout(function() {
    //   if(chip.hasClass('to-be-inactive'))
    //     chip.css('display', 'none').removeClass('to-be-inactive');
    // },500);
  });
  
  $(document).ready(function () {
    
    
    
  });

});
