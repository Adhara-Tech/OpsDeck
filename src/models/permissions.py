from ..extensions import db

class Module(db.Model):
    """
    Represents a logical module/section of the OpsDeck application.
    Used for assigning granular permissions in the future.
    """
    __tablename__ = 'module'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Module {self.slug}>'
