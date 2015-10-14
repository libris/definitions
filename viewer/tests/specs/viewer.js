describe('id.kb.se', function() {

  describe('Viewer', function() {
    
    before(function(client, done) {
      done();
    });
    
    after(function(client, done) {
      client.end(function() {
        done();
      });
    });
    
    afterEach(function(client, done) {
      done();
    });
    
    beforeEach(function(client, done) {
      done();
    });
    
    describe('Index', function() {
      it('Should be empty', function(client) {
        
        client
          .url('http://localhost:5000')
          .waitForElementPresent('body', 10000)
          .waitForElementPresent('main.container', 10000)
          .expect.element('main.container').text.to.equal('')  
      });
      
      it('Should have a navbar', function(client) {
        client
          .expect.element('.navbar').to.be.present
      });
      
    })
    
    describe('List', function() {
      it('Should show a list of collections', function(client) {
        
        client
          .url('http://localhost:5000/list/')
          .expect.element('main.container .list-group-item').to.be.present
      });
      
    })
    
  });

});
